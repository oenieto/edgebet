"""
Edgebet — motor de settlement de picks pasados.

Sprint 3 Mauricio.

Flujo principal (`settle_pending_picks`):
  1. Lee fixtures con status='finished'.
  2. Cruza con user_bets donde result='pending' por pick_id → match.
  3. Resuelve win/loss/void según el resultado real del fixture.
  4. Actualiza user_bets.result, pnl, settled_at.
  5. Actualiza bankroll_snapshots con el P&L diario.
  6. Actualiza user_ranks XP (win = 20 + (odds-1)*15, loss = 5, void = 0).
  7. Registra en settlement_log.

Reglas XP:
  win  → 20 + (odds - 1) * 15  (mínimo 20 XP)
  loss → 5 XP (participación)
  void → 0 XP
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from api.db import connect

logger = logging.getLogger("edgebet.settlement")


# ============================================================
# HELPERS
# ============================================================

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_result(prediction: str, home_score: int, away_score: int) -> str:
    """
    Devuelve 'win' | 'loss' | 'void' dada la predicción y el marcador final.
    prediction es 'home' | 'draw' | 'away'.
    """
    if home_score < 0 or away_score < 0:
        return "void"
    if home_score > away_score:
        actual = "home"
    elif home_score == away_score:
        actual = "draw"
    else:
        actual = "away"
    return "win" if prediction == actual else "loss"


def _compute_xp(result: str, odds: float | None) -> int:
    if result == "win":
        o = float(odds) if odds and odds > 1.0 else 1.0
        return max(20, int(round(20 + (o - 1) * 15)))
    if result == "loss":
        return 5
    return 0  # void


def _compute_pnl(result: str, stake: float, odds: float | None) -> float:
    if result == "win":
        o = float(odds) if odds and odds > 1.0 else 1.0
        return round(stake * (o - 1), 4)
    if result == "loss":
        return round(-stake, 4)
    return 0.0  # void


# ============================================================
# ENTRY POINT PRINCIPAL
# ============================================================

def settle_pending_picks() -> dict:
    """
    Resuelve todas las apuestas pendientes cuyo fixture ya está terminado.
    Devuelve un resumen serializable para el endpoint /settlement/run.
    """
    summary = {
        "picks_settled": 0,
        "wins": 0,
        "losses": 0,
        "voids": 0,
        "total_pnl": 0.0,
        "xp_awarded_total": 0,
        "errors": [],
        "run_at": _now_utc().isoformat(),
    }

    try:
        with connect() as cur:
            # 1. Apuestas pendientes
            try:
                cur.execute(
                    """
                    SELECT ub.id, ub.user_id, ub.pick_id, ub.match,
                           ub.prediction, ub.stake, ub.odds, ub.market
                    FROM user_bets ub
                    WHERE ub.result = 'pending'
                    """,
                )
                pending_bets = cur.fetchall()
            except Exception as exc:
                logger.warning("[settlement] no pude leer user_bets: %s", exc)
                return summary

            if not pending_bets:
                return summary

            # 2. Fixtures terminados indexados por match string (home vs away)
            try:
                cur.execute(
                    "SELECT id, home_team, away_team, home_score, away_score "
                    "FROM fixtures WHERE status = 'finished'"
                )
                finished_rows = cur.fetchall()
            except Exception as exc:
                logger.warning("[settlement] no pude leer fixtures: %s", exc)
                return summary

            finished: dict[str, dict] = {}
            for r in finished_rows:
                if hasattr(r, "__getitem__"):
                    key = f"{r['home_team']} vs {r['away_team']}".lower()
                    finished[key] = {
                        "home_score": r["home_score"],
                        "away_score": r["away_score"],
                    }
                else:
                    key = f"{r[1]} vs {r[2]}".lower()
                    finished[key] = {"home_score": r[3], "away_score": r[4]}

            # 3. Procesar cada apuesta pendiente
            now_str = _now_utc().isoformat()
            daily_pnl: dict[tuple[int, str], float] = {}  # (user_id, date) -> pnl

            for bet in pending_bets:
                if hasattr(bet, "__getitem__"):
                    bet_id      = bet["id"]
                    user_id     = bet["user_id"]
                    match_str   = (bet["match"] or "").lower()
                    prediction  = bet["prediction"]
                    stake       = float(bet["stake"] or 0)
                    odds        = bet["odds"]
                else:
                    bet_id, user_id, _pick_id, match_str_raw, prediction, stake, odds, _market = bet
                    match_str = (match_str_raw or "").lower()
                    stake = float(stake or 0)

                fixture_data = finished.get(match_str)
                if not fixture_data:
                    continue  # fixture aún no terminado o nombre no coincide

                try:
                    hs = int(fixture_data["home_score"] or 0)
                    as_ = int(fixture_data["away_score"] or 0)
                except (TypeError, ValueError):
                    result = "void"
                    hs = as_ = -1
                else:
                    result = _resolve_result(prediction, hs, as_)

                pnl = _compute_pnl(result, stake, odds)
                xp  = _compute_xp(result, odds)

                # 4a. Actualizar user_bets
                try:
                    cur.execute(
                        """
                        UPDATE user_bets
                        SET result=%s, pnl=%s, xp_awarded=%s, settled_at=%s
                        WHERE id=%s AND result='pending'
                        """,
                        (result, pnl, xp, now_str, bet_id),
                    )
                except Exception as exc:
                    logger.warning("[settlement] update bet %s falló: %s", bet_id, exc)
                    summary["errors"].append(f"bet {bet_id}: {exc}")
                    continue

                # Acumular P&L diario
                today = _now_utc().date().isoformat()
                daily_pnl[(user_id, today)] = daily_pnl.get((user_id, today), 0.0) + pnl

                # 4b. Actualizar user_ranks XP
                if xp > 0:
                    _update_user_xp(cur, user_id, xp, result, odds)

                summary["picks_settled"] += 1
                summary["total_pnl"] = round(summary["total_pnl"] + pnl, 4)
                summary["xp_awarded_total"] += xp
                if result == "win":
                    summary["wins"] += 1
                elif result == "loss":
                    summary["losses"] += 1
                else:
                    summary["voids"] += 1

            # 5. Actualizar bankroll_snapshots
            for (uid, date), day_pnl in daily_pnl.items():
                _upsert_bankroll_snapshot(cur, uid, date, day_pnl)

            # 6. Registrar en settlement_log (tabla puede no existir todavía)
            accuracy = None
            if (summary["wins"] + summary["losses"]) > 0:
                accuracy = round(
                    summary["wins"] / (summary["wins"] + summary["losses"]) * 100, 2
                )
            try:
                cur.execute(
                    """
                    INSERT INTO settlement_log
                        (picks_settled, total_pnl, accuracy_pct, notes)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        summary["picks_settled"],
                        summary["total_pnl"],
                        accuracy,
                        f"auto cron {now_str}",
                    ),
                )
            except Exception as exc:
                logger.warning("[settlement] settlement_log insert falló: %s", exc)

    except Exception as exc:
        logger.error("[settlement] settle_pending_picks error crítico: %s", exc)
        summary["errors"].append(str(exc))

    return summary


def _update_user_xp(cur, user_id: int, xp: int, result: str, odds: float | None) -> None:
    """Suma XP y actualiza contadores en user_ranks (idempotente por xp_awarded en bet)."""
    try:
        cur.execute(
            "SELECT total_xp, bets_won, bets_lost, biggest_win_odds "
            "FROM user_ranks WHERE user_id=%s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            # Primera vez — insertar
            cur.execute(
                """
                INSERT INTO user_ranks (user_id, total_xp, bets_won, bets_lost)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, xp, 1 if result == "win" else 0, 1 if result == "loss" else 0),
            )
            return

        if hasattr(row, "__getitem__"):
            total_xp        = int(row["total_xp"] or 0)
            bets_won        = int(row["bets_won"] or 0)
            bets_lost       = int(row["bets_lost"] or 0)
            biggest_win_odds = float(row["biggest_win_odds"] or 0)
        else:
            total_xp, bets_won, bets_lost, biggest_win_odds = (
                int(row[0] or 0), int(row[1] or 0), int(row[2] or 0), float(row[3] or 0)
            )

        new_total_xp = total_xp + xp
        new_won  = bets_won  + (1 if result == "win"  else 0)
        new_lost = bets_lost + (1 if result == "loss" else 0)
        new_biggest = biggest_win_odds
        if result == "win" and odds and float(odds) > biggest_win_odds:
            new_biggest = float(odds)

        cur.execute(
            """
            UPDATE user_ranks
            SET total_xp=%s, bets_won=%s, bets_lost=%s,
                biggest_win_odds=%s, last_evaluated_at=%s
            WHERE user_id=%s
            """,
            (new_total_xp, new_won, new_lost, new_biggest,
             _now_utc().isoformat(), user_id),
        )
        # Evaluar si cambió de rango
        _maybe_promote_rank(cur, user_id, new_total_xp)

    except Exception as exc:
        logger.warning("[settlement] _update_user_xp user %s falló: %s", user_id, exc)


def _maybe_promote_rank(cur, user_id: int, total_xp: int) -> None:
    """Sube o baja de rango si el XP cruza un umbral. Registra en rank_history."""
    try:
        cur.execute(
            "SELECT code, tier_index, min_xp FROM ranks ORDER BY tier_index DESC"
        )
        ranks = cur.fetchall()
        if not ranks:
            return

        new_rank_code = None
        for r in ranks:
            if hasattr(r, "__getitem__"):
                min_xp = int(r["min_xp"] or 0)
                code   = r["code"]
            else:
                code, _ti, min_xp = r[0], r[1], int(r[2] or 0)
            if total_xp >= min_xp:
                new_rank_code = code
                break

        if not new_rank_code:
            return

        cur.execute(
            "SELECT current_rank_code FROM user_ranks WHERE user_id=%s", (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return
        current = row["current_rank_code"] if hasattr(row, "__getitem__") else row[0]

        if current == new_rank_code:
            return

        # Determinar dirección
        cur.execute(
            "SELECT tier_index FROM ranks WHERE code=%s", (current,)
        )
        r_cur = cur.fetchone()
        cur.execute(
            "SELECT tier_index FROM ranks WHERE code=%s", (new_rank_code,)
        )
        r_new = cur.fetchone()
        if not r_cur or not r_new:
            return
        ti_cur = r_cur["tier_index"] if hasattr(r_cur, "__getitem__") else r_cur[0]
        ti_new = r_new["tier_index"] if hasattr(r_new, "__getitem__") else r_new[0]
        direction = "up" if ti_new > ti_cur else "down"

        cur.execute(
            "UPDATE user_ranks SET current_rank_code=%s WHERE user_id=%s",
            (new_rank_code, user_id),
        )
        cur.execute(
            """
            INSERT INTO rank_history
                (user_id, from_rank, to_rank, direction, total_xp_at_event)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, current, new_rank_code, direction, total_xp),
        )
    except Exception as exc:
        logger.warning("[settlement] _maybe_promote_rank user %s: %s", user_id, exc)


def _upsert_bankroll_snapshot(cur, user_id: int, date: str, pnl: float) -> None:
    """Suma el P&L del día al snapshot diario del usuario."""
    try:
        cur.execute(
            "SELECT id, amount, pnl_day, picks_count FROM bankroll_snapshots "
            "WHERE user_id=%s AND date=%s",
            (user_id, date),
        )
        row = cur.fetchone()
        if row:
            if hasattr(row, "__getitem__"):
                snap_id  = row["id"]
                amount   = float(row["amount"] or 0)
                pnl_day  = float(row["pnl_day"] or 0)
                picks    = int(row["picks_count"] or 0)
            else:
                snap_id, amount, pnl_day, picks = row[0], float(row[1] or 0), float(row[2] or 0), int(row[3] or 0)
            cur.execute(
                "UPDATE bankroll_snapshots SET amount=%s, pnl_day=%s, picks_count=%s "
                "WHERE id=%s",
                (round(amount + pnl, 4), round(pnl_day + pnl, 4), picks + 1, snap_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO bankroll_snapshots (user_id, date, amount, pnl_day, picks_count)
                VALUES (%s, %s, %s, %s, 1)
                """,
                (user_id, date, round(pnl, 4), round(pnl, 4)),
            )
    except Exception as exc:
        logger.warning("[settlement] bankroll_snapshot user %s: %s", user_id, exc)


# ============================================================
# MÉTRICAS ROLLING
# ============================================================

def compute_rolling_accuracy(user_id: int, days: int = 30) -> dict:
    """
    Calcula accuracy rolling, ROI y totales de un usuario en los últimos `days`.
    Devuelve datos sintéticos si no hay apuestas registradas (para desarrollo).
    """
    cutoff = (_now_utc() - timedelta(days=days)).isoformat()
    result = {
        "user_id": user_id,
        "days": days,
        "accuracy": 0.0,
        "total_bets": 0,
        "wins": 0,
        "losses": 0,
        "roi": 0.0,
        "total_staked": 0.0,
        "total_pnl": 0.0,
    }

    try:
        with connect() as cur:
            cur.execute(
                """
                SELECT result, stake, pnl
                FROM user_bets
                WHERE user_id=%s
                  AND result IN ('win','loss','void')
                  AND settled_at >= %s
                """,
                (user_id, cutoff),
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.warning("[settlement] compute_rolling_accuracy DB error: %s", exc)
        rows = []

    if not rows:
        return result

    wins = losses = voids = 0
    total_staked = total_pnl = 0.0

    for r in rows:
        if hasattr(r, "__getitem__"):
            res   = r["result"]
            stake = float(r["stake"] or 0)
            pnl   = float(r["pnl"] or 0)
        else:
            res, stake, pnl = r[0], float(r[1] or 0), float(r[2] or 0)

        if res == "win":
            wins += 1
        elif res == "loss":
            losses += 1
        else:
            voids += 1
        total_staked += stake
        total_pnl += pnl

    total_decided = wins + losses
    accuracy = round(wins / total_decided, 4) if total_decided > 0 else 0.0
    roi = round(total_pnl / total_staked, 4) if total_staked > 0 else 0.0

    result.update({
        "total_bets": wins + losses + voids,
        "wins": wins,
        "losses": losses,
        "accuracy": accuracy,
        "roi": roi,
        "total_staked": round(total_staked, 2),
        "total_pnl": round(total_pnl, 2),
    })
    return result


def compute_league_accuracy(days: int = 30) -> list[dict]:
    """
    Stats de accuracy agregados por liga para toda la plataforma.
    Útil para el panel de admin y el widget de métricas globales.
    """
    cutoff = (_now_utc() - timedelta(days=days)).isoformat()
    rows = []
    try:
        with connect() as cur:
            # user_bets no tiene league_slug — se une via pick_id a fixtures si
            # el match string se puede cruzar. Como aproximación, agrupamos por
            # el campo `market` que es lo que tenemos hoy. Si la tabla tiene
            # league info en el futuro, esta query se actualiza.
            cur.execute(
                """
                SELECT market,
                       COUNT(*) AS total,
                       SUM(CASE WHEN result='win'  THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN result='loss' THEN 1 ELSE 0 END) AS losses,
                       SUM(pnl) AS total_pnl,
                       SUM(stake) AS total_staked
                FROM user_bets
                WHERE result IN ('win','loss')
                  AND settled_at >= %s
                GROUP BY market
                """,
                (cutoff,),
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.warning("[settlement] compute_league_accuracy DB error: %s", exc)

    if not rows:
        # Datos sintéticos para desarrollo
        return _synth_league_accuracy()

    result = []
    for r in rows:
        if hasattr(r, "__getitem__"):
            market       = r["market"] or "ML"
            total        = int(r["total"] or 0)
            wins         = int(r["wins"] or 0)
            losses       = int(r["losses"] or 0)
            total_pnl    = float(r["total_pnl"] or 0)
            total_staked = float(r["total_staked"] or 0)
        else:
            market, total, wins, losses, total_pnl, total_staked = (
                r[0] or "ML", int(r[1] or 0), int(r[2] or 0),
                int(r[3] or 0), float(r[4] or 0), float(r[5] or 0),
            )
        decided = wins + losses
        result.append({
            "market": market,
            "total_bets": total,
            "wins": wins,
            "losses": losses,
            "accuracy": round(wins / decided, 4) if decided > 0 else 0.0,
            "roi": round(total_pnl / total_staked, 4) if total_staked > 0 else 0.0,
        })
    return result


def _synth_league_accuracy() -> list[dict]:
    leagues = [
        ("premier-league", 0.614, 0.18),
        ("la-liga",         0.587, 0.14),
        ("bundesliga",      0.602, 0.22),
        ("serie-a",         0.571, 0.11),
        ("ligue-1",         0.563, 0.09),
        ("champions-league", 0.541, 0.07),
    ]
    result = []
    for slug, acc, roi in leagues:
        total = 47
        wins  = int(total * acc)
        result.append({
            "market": slug,
            "total_bets": total,
            "wins": wins,
            "losses": total - wins,
            "accuracy": acc,
            "roi": roi,
        })
    return result
