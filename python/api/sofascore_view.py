"""
Edgebet — agregador estilo Sofascore.

Compone un payload unificado por match con:
  - Header: equipos, kickoff, status, score live (si hay)
  - Stats: posesión, remates, corners, tarjetas (con bars comparativos)
  - Eventos: goles, tarjetas, sustituciones cronológicos
  - Lineups: formación + starting XI + bench
  - H2H: últimos 5 enfrentamientos
  - Form: últimos 5 partidos por equipo
  - Odds: snapshot del bookmaker preferido

Si no hay datos (porque el feed externo aún no se conectó), devolvemos lo que
podemos calcular del histórico ya cacheado en `openfootball_loader` + `picks_service`.
Lo importante: el contrato del response es ESTABLE — el frontend no necesita
cambiar cuando integremos un feed real, solo se pueblan más campos.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from api.db import connect

logger = logging.getLogger("edgebet.sofascore")


def _safe_load_json(raw: Optional[str]) -> list:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []


def _fixture_header(fixture: dict) -> dict:
    return {
        "id": fixture.get("id"),
        "league_slug": fixture.get("league_slug"),
        "home_team": fixture.get("home_team"),
        "away_team": fixture.get("away_team"),
        "kickoff": str(fixture.get("kickoff")) if fixture.get("kickoff") else None,
        "venue": fixture.get("venue"),
        "status": fixture.get("status") or "scheduled",
        "minute": fixture.get("minute"),
        "score": {
            "home": fixture.get("home_score"),
            "away": fixture.get("away_score"),
        },
    }


def _build_stats_block(home_row: Optional[dict], away_row: Optional[dict]) -> dict:
    """Para cada métrica devolvemos {home, away, total} + bar pct para UI."""
    metrics = [
        ("possession_pct", "Posesión", "%"),
        ("shots", "Remates", ""),
        ("shots_on_target", "Remates a puerta", ""),
        ("corners", "Tiros de esquina", ""),
        ("fouls", "Faltas", ""),
        ("yellow_cards", "Amarillas", ""),
        ("red_cards", "Rojas", ""),
        ("offsides", "Offsides", ""),
        ("pass_accuracy_pct", "Precisión pase", "%"),
        ("expected_goals", "xG", ""),
    ]

    out: list[dict] = []
    for key, label, unit in metrics:
        h = (home_row or {}).get(key)
        a = (away_row or {}).get(key)
        if h is None and a is None:
            continue
        total = (h or 0) + (a or 0)
        h_bar = round(((h or 0) / total) * 100, 1) if total > 0 else 50.0
        out.append({
            "key": key, "label": label, "unit": unit,
            "home": h, "away": a,
            "home_bar_pct": h_bar, "away_bar_pct": round(100 - h_bar, 1),
        })
    return {"available": bool(out), "metrics": out}


def _build_events(rows: list[dict]) -> list[dict]:
    return [
        {
            "minute": r["minute"], "side": r["side"], "type": r["event_type"],
            "player": r.get("player_name"), "detail": r.get("detail"),
        }
        for r in rows
    ]


def _build_lineup(row: Optional[dict]) -> Optional[dict]:
    if not row:
        return None
    return {
        "formation": row.get("formation"),
        "starting_xi": _safe_load_json(row.get("starting_xi")),
        "bench": _safe_load_json(row.get("bench")),
        "coach": row.get("coach"),
    }


def _h2h_block(home_team: str, away_team: str) -> dict:
    with connect() as cur:
        cur.execute(
            "SELECT * FROM h2h_cache WHERE home_team=%s AND away_team=%s",
            (home_team, away_team),
        )
        row = cur.fetchone()
    if not row:
        return {"available": False, "matches": [], "summary": None}
    matches = _safe_load_json(row["last_n_matches"])
    return {
        "available": True,
        "matches": matches,
        "summary": {
            "home_wins": row["home_wins"],
            "draws": row["draws"],
            "away_wins": row["away_wins"],
            "avg_total_goals": row["avg_total_goals"],
        },
    }


def _latest_odds(fixture_id: int) -> Optional[dict]:
    with connect() as cur:
        cur.execute(
            "SELECT * FROM odds_snapshots WHERE fixture_id=%s "
            "ORDER BY captured_at DESC LIMIT 1",
            (fixture_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "bookmaker": row["bookmaker"],
        "captured_at": str(row["captured_at"]),
        "h2h": {"home": row["home_odds"], "draw": row["draw_odds"], "away": row["away_odds"]},
        "totals_2_5": {"over": row["over_2_5_odds"], "under": row["under_2_5_odds"]},
    }


def build_match_view(fixture_id: int) -> Optional[dict]:
    """
    Compone el payload unificado para un fixture. None si no existe.
    """
    with connect() as cur:
        cur.execute("SELECT * FROM fixtures WHERE id=%s", (fixture_id,))
        fx_row = cur.fetchone()
        if not fx_row:
            return None
        fixture = dict(fx_row)

        cur.execute("SELECT * FROM match_stats WHERE fixture_id=%s ORDER BY captured_at DESC", (fixture_id,))
        stats_rows = [dict(r) for r in cur.fetchall()]
        home_stats = next((s for s in stats_rows if s["side"] == "home"), None)
        away_stats = next((s for s in stats_rows if s["side"] == "away"), None)

        cur.execute(
            "SELECT * FROM match_events WHERE fixture_id=%s ORDER BY minute ASC",
            (fixture_id,),
        )
        events_rows = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM match_lineups WHERE fixture_id=%s", (fixture_id,))
        lineup_rows = [dict(r) for r in cur.fetchall()]
        home_lineup = next((l for l in lineup_rows if l["side"] == "home"), None)
        away_lineup = next((l for l in lineup_rows if l["side"] == "away"), None)

    return {
        "header": _fixture_header(fixture),
        "stats": _build_stats_block(home_stats, away_stats),
        "events": _build_events(events_rows),
        "lineups": {
            "home": _build_lineup(home_lineup),
            "away": _build_lineup(away_lineup),
        },
        "h2h": _h2h_block(fixture["home_team"], fixture["away_team"]),
        "odds": _latest_odds(fixture_id),
    }


def build_match_view_by_pick_id(pick_id: str) -> Optional[dict]:
    """
    Hook para pick_id (UUID): busca un fixture cuyo home/away coincida con el
    match del pick. Si no hay fixture persistido, retorna None — el caller
    debería fallback a /picks/{id}/stats que sí computa desde histórico.
    """
    from api.picks_service import get_todays_picks
    pool = get_todays_picks(league_slug=None)
    pick = next((p for p in pool if p["id"] == pick_id), None)
    if not pick:
        return None
    home, away = pick["homeTeam"], pick["awayTeam"]
    with connect() as cur:
        cur.execute(
            "SELECT id FROM fixtures WHERE home_team=%s AND away_team=%s "
            "ORDER BY kickoff DESC LIMIT 1",
            (home, away),
        )
        row = cur.fetchone()
    if not row:
        return None
    return build_match_view(row["id"])
