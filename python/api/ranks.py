"""
Edgebet — sistema de rangos, XP y achievements.

Filosofía:
  - Premiar VOLUMEN moderado y DECISIONES de calidad, no suerte pura.
  - Longshot bonus: ganar a cuotas altas vale más (señal de edge real).
  - Penalización suave en rachas perdedoras: reduces XP, no bajas de rango.

Cálculo XP por apuesta resuelta:
  base       = stake * (odds - 1)         # ganancia neta del win (en stake-units)
  longshot   = factor que crece con odds  # 1.0 hasta 1.50, hasta 2.5x en 5.00+
  result_mul = win → +1; void → 0; loss → -0.10  (pérdida ligera, no ganas pero no te aplastas)
  xp_raw     = base * 25 * longshot * result_mul

Ejemplo: stake $10, odds 1.85, WIN → 10*0.85*25*1.0 = ~213 XP
         stake $10, odds 3.50, WIN → 10*2.50*25*1.85 = ~1156 XP (longshot premium)
         stake $10, odds 1.85, LOSS → 10*0.85*25*-0.10 = ~-21 XP

Después se evalúa el rango: el `current_rank_code` se ajusta al rango más alto
cuyo `min_xp <= total_xp`. NO bajamos de rango aunque XP caiga (sticky-up).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from api.db import connect


# Multiplicadores de longshot — calibrados con curva tipo Kelly:
# odds bajos (favorito) → multiplicador 1, odds altos premian más.
def _longshot_multiplier(odds: float) -> float:
    if odds <= 1.50:
        return 1.0
    if odds <= 2.00:
        return 1.20
    if odds <= 2.50:
        return 1.50
    if odds <= 3.50:
        return 1.85
    if odds <= 5.00:
        return 2.20
    return 2.50  # 5.00+


def calculate_xp(stake: float, odds: float, result: str) -> int:
    """XP para una apuesta resuelta. Idempotente — depende solo de inputs."""
    if result not in {"win", "loss", "void"}:
        return 0
    if result == "void":
        return 0
    base = stake * (odds - 1.0)
    longshot = _longshot_multiplier(odds)
    if result == "win":
        result_mul = 1.0
    else:  # loss
        # Pérdida ligera para que rachas malas no destruyan progreso, pero
        # tampoco salga gratis perder. Calibrado a -10% del XP que habría
        # ganado el win equivalente.
        result_mul = -0.10
    xp = base * 25.0 * longshot * result_mul
    return int(round(xp))


@dataclass
class RankInfo:
    code: str
    name: str
    tier_index: int
    min_xp: int
    color_hex: str
    icon: str
    description: str


def list_ranks() -> list[RankInfo]:
    with connect() as cur:
        cur.execute(
            "SELECT code, name, tier_index, min_xp, color_hex, icon, description "
            "FROM ranks ORDER BY tier_index ASC"
        )
        rows = cur.fetchall()
    return [RankInfo(**dict(r)) for r in rows]


def _ranks_descending() -> list[RankInfo]:
    return sorted(list_ranks(), key=lambda r: r.tier_index, reverse=True)


def evaluate_rank(total_xp: int, current_code: str, ranks_desc: Optional[list[RankInfo]] = None) -> RankInfo:
    """
    Devuelve el rango más alto alcanzado dado total_xp.
    Sticky-up: si el current_code ya supera al evaluado por XP (caso teórico
    con XP negativo), se mantiene en current_code.
    """
    ranks = ranks_desc or _ranks_descending()
    earned = next((r for r in ranks if total_xp >= r.min_xp), ranks[-1])
    current = next((r for r in ranks if r.code == current_code), earned)
    return earned if earned.tier_index >= current.tier_index else current


def ensure_user_rank_row(user_id: int) -> None:
    """Crea fila en user_ranks si no existe (idempotente)."""
    with connect() as cur:
        cur.execute("SELECT user_id FROM user_ranks WHERE user_id = %s", (user_id,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO user_ranks (user_id, current_rank_code, total_xp) "
                "VALUES (%s, 'rookie', 0)",
                (user_id,),
            )


def get_user_rank_state(user_id: int) -> dict:
    """Snapshot completo del estado de rango del usuario para el frontend."""
    ensure_user_rank_row(user_id)
    with connect() as cur:
        cur.execute(
            "SELECT current_rank_code, total_xp, bets_won, bets_lost, longshot_wins, "
            "biggest_win_odds, streak_current, streak_best "
            "FROM user_ranks WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
    state = dict(row) if row else {
        "current_rank_code": "rookie", "total_xp": 0, "bets_won": 0,
        "bets_lost": 0, "longshot_wins": 0, "biggest_win_odds": 0,
        "streak_current": 0, "streak_best": 0,
    }
    ranks = _ranks_descending()
    current = next((r for r in ranks if r.code == state["current_rank_code"]), ranks[-1])
    next_rank = None
    for r in sorted(ranks, key=lambda x: x.tier_index):
        if r.tier_index > current.tier_index:
            next_rank = r
            break

    progress_pct = 100.0
    if next_rank:
        span = next_rank.min_xp - current.min_xp
        within = state["total_xp"] - current.min_xp
        progress_pct = max(0.0, min(100.0, (within / span) * 100)) if span > 0 else 100.0

    return {
        **state,
        "current": _rank_to_dict(current),
        "next": _rank_to_dict(next_rank) if next_rank else None,
        "progress_pct": round(progress_pct, 1),
        "xp_to_next": max(0, (next_rank.min_xp - state["total_xp"]) if next_rank else 0),
    }


def _rank_to_dict(r: Optional[RankInfo]) -> Optional[dict]:
    if r is None:
        return None
    return {
        "code": r.code, "name": r.name, "tier_index": r.tier_index,
        "min_xp": r.min_xp, "color_hex": r.color_hex, "icon": r.icon,
        "description": r.description,
    }


# ============================================================
# SETTLEMENT — punto único de awarding XP + evaluar achievements + rank-up
# ============================================================
def settle_bet(bet_id: int) -> dict:
    """
    Liquida una apuesta y aplica todos los efectos en cadena:
      1. Calcula XP según resultado (idempotente vía xp_awarded).
      2. Suma XP al usuario, actualiza contadores.
      3. Reevalúa rango — si subió, persiste rank_history.
      4. Evalúa achievements desbloqueables → suma XP de bonus.
    Devuelve un summary del cambio (útil para mostrar toast en UI).
    """
    with connect() as cur:
        cur.execute("SELECT * FROM user_bets WHERE id = %s", (bet_id,))
        bet = cur.fetchone()
        if not bet:
            raise ValueError(f"bet_id {bet_id} no existe")
        bet = dict(bet)

        if bet.get("xp_awarded", 0) > 0:
            return {"already_settled": True, "bet_id": bet_id, "xp_awarded": bet["xp_awarded"]}

        if bet.get("result") not in {"win", "loss", "void"}:
            raise ValueError(f"bet result inválido para settle: {bet.get('result')!r}")

        user_id = bet["user_id"]
        xp_for_bet = calculate_xp(float(bet["stake"]), float(bet["odds"] or 0), bet["result"])

        ensure_user_rank_row(user_id)
        cur.execute(
            "SELECT current_rank_code, total_xp, bets_won, bets_lost, longshot_wins, "
            "biggest_win_odds, streak_current, streak_best "
            "FROM user_ranks WHERE user_id = %s",
            (user_id,),
        )
        rank_row = dict(cur.fetchone())

        new_total_xp = max(0, rank_row["total_xp"] + xp_for_bet)
        new_won = rank_row["bets_won"] + (1 if bet["result"] == "win" else 0)
        new_lost = rank_row["bets_lost"] + (1 if bet["result"] == "loss" else 0)
        is_longshot_win = bet["result"] == "win" and float(bet["odds"] or 0) >= 2.50
        new_longshot = rank_row["longshot_wins"] + (1 if is_longshot_win else 0)
        new_biggest = max(float(rank_row["biggest_win_odds"] or 0),
                          float(bet["odds"] or 0) if bet["result"] == "win" else 0)
        if bet["result"] == "win":
            new_streak = rank_row["streak_current"] + 1
        elif bet["result"] == "loss":
            new_streak = 0
        else:
            new_streak = rank_row["streak_current"]
        new_streak_best = max(rank_row["streak_best"], new_streak)

        new_rank = evaluate_rank(new_total_xp, rank_row["current_rank_code"])
        rank_changed = new_rank.code != rank_row["current_rank_code"]

        cur.execute(
            "UPDATE user_ranks SET current_rank_code=%s, total_xp=%s, bets_won=%s, "
            "bets_lost=%s, longshot_wins=%s, biggest_win_odds=%s, streak_current=%s, "
            "streak_best=%s, last_evaluated_at=CURRENT_TIMESTAMP WHERE user_id=%s",
            (new_rank.code, new_total_xp, new_won, new_lost, new_longshot,
             new_biggest, new_streak, new_streak_best, user_id),
        )
        cur.execute("UPDATE user_bets SET xp_awarded=%s, settled_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (xp_for_bet, bet_id))

        if rank_changed:
            cur.execute(
                "INSERT INTO rank_history (user_id, from_rank, to_rank, direction, "
                "total_xp_at_event, triggered_by_bet_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, rank_row["current_rank_code"], new_rank.code, "up",
                 new_total_xp, bet_id),
            )

        # Evaluar achievements DESPUÉS del update — usa contadores frescos
        unlocked = _evaluate_achievements(cur, user_id, {
            "total_bets": new_won + new_lost,
            "won_odds": float(bet["odds"] or 0) if bet["result"] == "win" else 0,
            "current_streak": new_streak,
        })

        # Achievements pueden dar XP — aplicar si los hay
        bonus_xp = sum(int(a["xp_reward"]) for a in unlocked)
        if bonus_xp:
            cur.execute("UPDATE user_ranks SET total_xp = total_xp + %s WHERE user_id = %s",
                        (bonus_xp, user_id))
            new_total_xp += bonus_xp
            # Reevaluar rango por si los bonus cruzan threshold
            new_rank2 = evaluate_rank(new_total_xp, new_rank.code)
            if new_rank2.code != new_rank.code:
                cur.execute(
                    "INSERT INTO rank_history (user_id, from_rank, to_rank, direction, "
                    "total_xp_at_event, triggered_by_bet_id) VALUES (%s, %s, %s, %s, %s, %s)",
                    (user_id, new_rank.code, new_rank2.code, "up", new_total_xp, bet_id),
                )
                cur.execute("UPDATE user_ranks SET current_rank_code=%s WHERE user_id=%s",
                            (new_rank2.code, user_id))
                new_rank = new_rank2

    return {
        "bet_id": bet_id, "xp_awarded": xp_for_bet, "bonus_xp": bonus_xp,
        "total_xp": new_total_xp, "rank_changed": rank_changed,
        "from_rank": rank_row["current_rank_code"] if rank_changed else None,
        "to_rank": new_rank.code,
        "achievements_unlocked": [a["code"] for a in unlocked],
    }


def _evaluate_achievements(cur, user_id: int, ctx: dict) -> list[dict]:
    """
    Evalúa qué achievements desbloquear AHORA. Retorna los nuevos.
    Reglas mapeadas por code (las definiciones viven en schema.ACHIEVEMENT_SEEDS):
    """
    cur.execute("SELECT achievement_code FROM user_achievements WHERE user_id = %s", (user_id,))
    already = {row["achievement_code"] for row in cur.fetchall()}

    triggered_codes: list[str] = []
    if ctx["total_bets"] >= 1 and "first_bet" not in already:
        triggered_codes.append("first_bet")
    if ctx["total_bets"] >= 10 and "ten_bets" not in already:
        triggered_codes.append("ten_bets")
    if ctx["total_bets"] >= 50 and "fifty_bets" not in already:
        triggered_codes.append("fifty_bets")
    if ctx["total_bets"] >= 100 and "hundred_bets" not in already:
        triggered_codes.append("hundred_bets")

    won_odds = ctx["won_odds"]
    if won_odds >= 2.50 and "longshot_2" not in already:
        triggered_codes.append("longshot_2")
    if won_odds >= 3.00 and "longshot_3" not in already:
        triggered_codes.append("longshot_3")
    if won_odds >= 5.00 and "longshot_5" not in already:
        triggered_codes.append("longshot_5")

    if ctx["current_streak"] >= 3 and "streak_3" not in already:
        triggered_codes.append("streak_3")
    if ctx["current_streak"] >= 5 and "streak_5" not in already:
        triggered_codes.append("streak_5")
    if ctx["current_streak"] >= 10 and "streak_10" not in already:
        triggered_codes.append("streak_10")

    if not triggered_codes:
        return []

    # Insertar y devolver con metadata
    placeholders = ",".join(["%s"] * len(triggered_codes))
    cur.execute(
        f"SELECT code, xp_reward FROM achievements WHERE code IN ({placeholders})",
        tuple(triggered_codes),
    )
    rewards = {row["code"]: row["xp_reward"] for row in cur.fetchall()}

    out: list[dict] = []
    for code in triggered_codes:
        cur.execute(
            "INSERT INTO user_achievements (user_id, achievement_code) VALUES (%s, %s)",
            (user_id, code),
        )
        out.append({"code": code, "xp_reward": rewards.get(code, 0)})
    return out


def list_user_achievements(user_id: int) -> list[dict]:
    """Logros desbloqueados + locked con metadata para vitrina del perfil."""
    with connect() as cur:
        cur.execute("""
            SELECT a.code, a.name, a.description, a.category, a.xp_reward, a.icon, a.rarity,
                   ua.unlocked_at
            FROM achievements a
            LEFT JOIN user_achievements ua
              ON ua.achievement_code = a.code AND ua.user_id = %s
            ORDER BY a.category, a.xp_reward
        """, (user_id,))
        rows = cur.fetchall()
    return [
        {
            "code": r["code"], "name": r["name"], "description": r["description"],
            "category": r["category"], "xp_reward": r["xp_reward"],
            "icon": r["icon"], "rarity": r["rarity"],
            "unlocked": r["unlocked_at"] is not None,
            "unlocked_at": str(r["unlocked_at"]) if r["unlocked_at"] else None,
        }
        for r in rows
    ]
