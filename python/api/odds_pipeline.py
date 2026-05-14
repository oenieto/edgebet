"""
Edgebet — pipeline de snapshots de odds cada 4h + detección de steam moves.

Sprint 1 Mauricio.

Diseño:
  - `run_odds_snapshot()`: recorre todas las ligas configuradas, llama a
    odds_provider.fetch_league_odds() y persiste en odds_snapshots. Si no hay
    API key, genera snapshots sintéticos con drift realista para que el UI
    tenga datos de desarrollo.
  - `calculate_steam_move()`: compara el snapshot más antiguo dentro de la
    ventana `hours` contra el más reciente y clasifica la magnitud del movimiento.
  - `get_odds_history()`: devuelve la serie temporal ordenada (útil para la
    sparkline del frontend).
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from api.db import connect


def _odds_provider():
    """Lazy import to avoid hard dependency on `requests` at module level."""
    from api.odds_provider import fetch_league_odds, is_configured
    return fetch_league_odds, is_configured

logger = logging.getLogger("edgebet.odds_pipeline")

# Ligas para las que corremos el snapshot (mismas que odds_provider)
_LEAGUES = [
    "premier-league",
    "la-liga",
    "bundesliga",
    "serie-a",
    "ligue-1",
    "champions-league",
]

# Bookmakers sintéticos cuando no hay API key real
_SYNTH_BOOKMAKERS = ["pinnacle", "bet365", "unibet"]


# ============================================================
# HELPERS INTERNOS
# ============================================================

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _synthetic_odds_for_fixture(fixture_id: int, rng: random.Random) -> dict:
    """Genera cuotas sintéticas realistas con leve drift respecto al fixture_id."""
    # Semilla determinista basada en fixture para que el drift sea coherente
    base_home = rng.uniform(1.50, 3.50)
    base_draw = rng.uniform(2.80, 4.00)
    base_away = rng.uniform(1.60, 4.00)
    over = rng.uniform(1.60, 2.20)
    under = rng.uniform(1.70, 2.30)
    return {
        "bookmaker": rng.choice(_SYNTH_BOOKMAKERS),
        "market": "h2h+totals",
        "home_odds": round(base_home, 2),
        "draw_odds": round(base_draw, 2),
        "away_odds": round(base_away, 2),
        "over_2_5_odds": round(over, 2),
        "under_2_5_odds": round(under, 2),
    }


def _drift(value: float, magnitude: float, rng: random.Random) -> float:
    """Aplica un pequeño drift aleatorio alrededor de `value`."""
    return round(max(1.05, value + rng.uniform(-magnitude, magnitude)), 2)


def _persist_snapshot(
    cur,
    fixture_id: int,
    bookmaker: str,
    market: str,
    home_odds: float | None,
    draw_odds: float | None,
    away_odds: float | None,
    over_2_5_odds: float | None,
    under_2_5_odds: float | None,
) -> None:
    cur.execute(
        """
        INSERT INTO odds_snapshots
            (fixture_id, bookmaker, market,
             home_odds, draw_odds, away_odds,
             over_2_5_odds, under_2_5_odds)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            fixture_id, bookmaker, market,
            home_odds, draw_odds, away_odds,
            over_2_5_odds, under_2_5_odds,
        ),
    )


# ============================================================
# API PÚBLICA
# ============================================================

def run_odds_snapshot() -> dict:
    """
    Entry point del cron cada 4h.
    Devuelve un resumen: {"leagues_processed": int, "fixtures_snapshotted": int,
                          "synthetic": bool, "errors": list[str]}.
    """
    summary = {
        "leagues_processed": 0,
        "fixtures_snapshotted": 0,
        "synthetic": True,
        "errors": [],
        "run_at": _now_utc().isoformat(),
    }

    try:
        fetch_league_odds, is_configured = _odds_provider()
        summary["synthetic"] = not is_configured()
    except Exception:
        fetch_league_odds = None
        is_configured = lambda: False

    for league_slug in _LEAGUES:
        try:
            if fetch_league_odds and is_configured():
                odds_list = fetch_league_odds(league_slug)
                _snapshot_from_real(league_slug, odds_list)
                summary["fixtures_snapshotted"] += len(odds_list)
            else:
                count = _snapshot_synthetic(league_slug)
                summary["fixtures_snapshotted"] += count
            summary["leagues_processed"] += 1
        except Exception as exc:
            msg = f"{league_slug}: {exc}"
            logger.warning("[odds_pipeline] snapshot falló — %s", msg)
            summary["errors"].append(msg)

    return summary


def _snapshot_from_real(league_slug: str, odds_list: list[dict]) -> None:
    """Persiste snapshots desde cuotas reales ya cargadas por odds_provider."""
    if not odds_list:
        return
    try:
        with connect() as cur:
            for entry in odds_list:
                cur.execute(
                    "SELECT id FROM fixtures WHERE league_slug=%s AND home_team=%s AND away_team=%s",
                    (league_slug, entry["home_team"], entry["away_team"]),
                )
                row = cur.fetchone()
                if not row:
                    continue
                fixture_id = row["id"] if hasattr(row, "__getitem__") else row[0]
                _persist_snapshot(
                    cur,
                    fixture_id=fixture_id,
                    bookmaker=entry.get("bookmaker", "unknown"),
                    market="h2h+totals",
                    home_odds=entry["h2h"].get("home"),
                    draw_odds=entry["h2h"].get("draw"),
                    away_odds=entry["h2h"].get("away"),
                    over_2_5_odds=entry["totals_2_5"].get("over"),
                    under_2_5_odds=entry["totals_2_5"].get("under"),
                )
    except Exception as exc:
        logger.warning("[odds_pipeline] _snapshot_from_real falló: %s", exc)


def _snapshot_synthetic(league_slug: str) -> int:
    """
    Para desarrollo: genera snapshots sintéticos con drift para todos los
    fixtures scheduled de la liga.
    """
    count = 0
    try:
        with connect() as cur:
            cur.execute(
                "SELECT id FROM fixtures WHERE league_slug=%s AND status=%s",
                (league_slug, "scheduled"),
            )
            rows = cur.fetchall()
            if not rows:
                return 0
            for row in rows:
                fixture_id = row["id"] if hasattr(row, "__getitem__") else row[0]
                rng = random.Random(fixture_id)
                snap = _synthetic_odds_for_fixture(fixture_id, rng)
                _persist_snapshot(
                    cur,
                    fixture_id=fixture_id,
                    **snap,
                )
                count += 1
    except Exception as exc:
        logger.warning("[odds_pipeline] _snapshot_synthetic %s falló: %s", league_slug, exc)
    return count


def get_odds_history(fixture_id: int, hours: int = 48) -> list[dict]:
    """
    Devuelve snapshots ordenados de más viejo a más nuevo dentro de la
    ventana `hours` para el fixture dado.

    Si no hay snapshots reales, genera una serie sintética de desarrollo
    con drift realista para que la sparkline tenga datos.
    """
    cutoff = (_now_utc() - timedelta(hours=hours)).isoformat()

    try:
        with connect() as cur:
            cur.execute(
                """
                SELECT bookmaker, market,
                       home_odds, draw_odds, away_odds,
                       over_2_5_odds, under_2_5_odds,
                       captured_at
                FROM odds_snapshots
                WHERE fixture_id = %s
                  AND captured_at >= %s
                ORDER BY captured_at ASC
                """,
                (fixture_id, cutoff),
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.warning("[odds_pipeline] get_odds_history DB error: %s", exc)
        rows = []

    if rows:
        return [
            {
                "bookmaker": r["bookmaker"] if hasattr(r, "__getitem__") else r[0],
                "market":    r["market"]    if hasattr(r, "__getitem__") else r[1],
                "home_odds": r["home_odds"] if hasattr(r, "__getitem__") else r[2],
                "draw_odds": r["draw_odds"] if hasattr(r, "__getitem__") else r[3],
                "away_odds": r["away_odds"] if hasattr(r, "__getitem__") else r[4],
                "over_2_5":  r["over_2_5_odds"]  if hasattr(r, "__getitem__") else r[5],
                "under_2_5": r["under_2_5_odds"] if hasattr(r, "__getitem__") else r[6],
                "captured_at": str(r["captured_at"] if hasattr(r, "__getitem__") else r[7]),
            }
            for r in rows
        ]

    # Fallback sintético: serie de 12 puntos cada 4h con drift acumulativo
    return _synth_history_series(fixture_id, hours)


def _synth_history_series(fixture_id: int, hours: int) -> list[dict]:
    """Serie histórica sintética para UI de desarrollo."""
    rng = random.Random(fixture_id + 9999)
    base_home = rng.uniform(1.70, 3.20)
    base_draw = rng.uniform(2.90, 3.80)
    base_away = rng.uniform(1.80, 3.50)
    base_over = rng.uniform(1.65, 2.10)
    base_under = rng.uniform(1.75, 2.15)

    interval_h = 4
    n_points = max(1, hours // interval_h)
    now = _now_utc()
    result = []

    h, d, a, ov, un = base_home, base_draw, base_away, base_over, base_under
    for i in range(n_points):
        ts = (now - timedelta(hours=hours - i * interval_h)).isoformat()
        h = _drift(h, 0.05, rng)
        d = _drift(d, 0.03, rng)
        a = _drift(a, 0.05, rng)
        ov = _drift(ov, 0.04, rng)
        un = _drift(un, 0.04, rng)
        result.append({
            "bookmaker": "synthetic",
            "market": "h2h+totals",
            "home_odds": h,
            "draw_odds": d,
            "away_odds": a,
            "over_2_5": ov,
            "under_2_5": un,
            "captured_at": ts,
        })
    return result


def calculate_steam_move(fixture_id: int, hours: int = 24) -> dict:
    """
    Compara el snapshot más antiguo vs el más reciente dentro de `hours` y
    determina si hay un steam move significativo.

    Devuelve:
        {
          "home_move": float,      # diferencia en cuota (positivo = subió, i.e. equipo bajó en prob)
          "draw_move": float,
          "away_move": float,
          "direction": str,        # "home_shortening" | "away_shortening" | "draw_shortening" | "mixed" | "stable"
          "magnitude": str,        # "strong" | "moderate" | "weak" | "none"
          "first_snapshot": str,   # ISO timestamp del primer snapshot
          "last_snapshot": str,    # ISO timestamp del último snapshot
        }
    """
    history = get_odds_history(fixture_id, hours)

    empty = {
        "home_move": 0.0,
        "draw_move": 0.0,
        "away_move": 0.0,
        "direction": "stable",
        "magnitude": "none",
        "first_snapshot": None,
        "last_snapshot": None,
    }

    if len(history) < 2:
        return empty

    first = history[0]
    last = history[-1]

    def _safe(val) -> float:
        try:
            return float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    home_move = round(_safe(last["home_odds"]) - _safe(first["home_odds"]), 3)
    draw_move = round(_safe(last["draw_odds"]) - _safe(first["draw_odds"]), 3)
    away_move = round(_safe(last["away_odds"]) - _safe(first["away_odds"]), 3)

    # Movimiento negativo en cuota = acortamiento (más probabilidad) = steam
    moves = {"home": home_move, "draw": draw_move, "away": away_move}
    shortening = {k: v for k, v in moves.items() if v < -0.05}

    if not shortening:
        direction = "stable"
        magnitude = "none"
    elif len(shortening) == 1:
        outcome = list(shortening.keys())[0]
        direction = f"{outcome}_shortening"
        abs_move = abs(list(shortening.values())[0])
        if abs_move >= 0.30:
            magnitude = "strong"
        elif abs_move >= 0.15:
            magnitude = "moderate"
        else:
            magnitude = "weak"
    else:
        direction = "mixed"
        max_abs = max(abs(v) for v in shortening.values())
        if max_abs >= 0.30:
            magnitude = "strong"
        elif max_abs >= 0.15:
            magnitude = "moderate"
        else:
            magnitude = "weak"

    return {
        "home_move": home_move,
        "draw_move": draw_move,
        "away_move": away_move,
        "direction": direction,
        "magnitude": magnitude,
        "first_snapshot": first.get("captured_at"),
        "last_snapshot": last.get("captured_at"),
    }
