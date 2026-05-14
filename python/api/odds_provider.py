"""
Edgebet — proveedor de odds reales.

Integración primaria: The Odds API (https://the-odds-api.com).
  - Free tier: 500 requests/mes, sin tarjeta.
  - Devuelve odds en tiempo real de bet365, pinnacle, unibet, etc.
  - Mercados: h2h (1X2), totals (over/under), spreads.

Diseño:
  - Si no hay API key (`EDGEBET_ODDS_API_KEY`), `is_configured()` → False y
    los endpoints devuelven 503 con mensaje claro. Evita romper el dashboard.
  - Cache en disco (data/cache/odds_*.json) con TTL configurable. Importante:
    cada call al provider quema 1 req del free tier.
  - Persistimos en odds_snapshots para tener historial de movimientos.
  - Compatible con el circuit breaker de polymarket: si la red falla, no
    disparamos pánico, solo loggeamos y seguimos.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from api.db import connect

API_BASE = "https://api.the-odds-api.com/v4"
SPORT_KEY_BY_LEAGUE = {
    "premier-league": "soccer_epl",
    "la-liga": "soccer_spain_la_liga",
    "bundesliga": "soccer_germany_bundesliga",
    "serie-a": "soccer_italy_serie_a",
    "ligue-1": "soccer_france_ligue_one",
    "champions-league": "soccer_uefa_champs_league",
}

# Bookmakers preferidos — orden de prioridad para extraer odds canónicos.
PREFERRED_BOOKMAKERS = ("pinnacle", "bet365", "williamhill", "unibet", "draftkings")

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_TTL_SECONDS = 60 * 5   # 5 min — odds reales se mueven, no queremos data vieja
REQUEST_TIMEOUT = 6

logger = logging.getLogger("edgebet.odds")


def _api_key() -> Optional[str]:
    return os.environ.get("EDGEBET_ODDS_API_KEY") or None


def is_configured() -> bool:
    return _api_key() is not None


def _cache_path(key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"odds_{h}.json"


def _read_cache(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        if (time.time() - path.stat().st_mtime) > CACHE_TTL_SECONDS:
            return None
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(path: Path, payload: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
    except OSError as exc:
        logger.warning("[odds] no pude escribir cache %s: %s", path, exc)


@dataclass
class OddsLine:
    bookmaker: str
    home: float
    draw: float | None
    away: float
    over_2_5: float | None
    under_2_5: float | None
    last_update: str


def _extract_h2h(bookmaker_block: dict) -> tuple[float | None, float | None, float | None]:
    """Saca home/draw/away de un bloque markets[].outcomes."""
    h2h = next((m for m in bookmaker_block.get("markets", []) if m.get("key") == "h2h"), None)
    if not h2h:
        return None, None, None
    home = draw = away = None
    for o in h2h.get("outcomes", []):
        name = (o.get("name") or "").lower()
        price = o.get("price")
        if name == "draw":
            draw = price
        elif name == bookmaker_block.get("_home_lower"):
            home = price
        elif name == bookmaker_block.get("_away_lower"):
            away = price
    return home, draw, away


def _extract_totals(bookmaker_block: dict, line: float = 2.5) -> tuple[float | None, float | None]:
    totals = next((m for m in bookmaker_block.get("markets", []) if m.get("key") == "totals"), None)
    if not totals:
        return None, None
    over = under = None
    for o in totals.get("outcomes", []):
        if abs(float(o.get("point", 0)) - line) > 0.01:
            continue
        name = (o.get("name") or "").lower()
        price = o.get("price")
        if name == "over":
            over = price
        elif name == "under":
            under = price
    return over, under


def fetch_league_odds(league_slug: str) -> list[dict]:
    """
    Devuelve lista de fixtures con odds normalizados por bookmaker.
    Vacía si no hay API key o la red está caída.
    """
    sport_key = SPORT_KEY_BY_LEAGUE.get(league_slug)
    if not sport_key:
        return []
    if not is_configured():
        logger.info("[odds] sin EDGEBET_ODDS_API_KEY — saltando fetch para %s", league_slug)
        return []

    cache_key = f"league:{sport_key}"
    cached = _read_cache(_cache_path(cache_key))
    if cached is not None:
        return cached

    url = f"{API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": _api_key(),
        "regions": "eu,uk,us",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
    }
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        logger.warning("[odds] %s falló: %s", league_slug, exc)
        return []

    if resp.status_code == 401:
        logger.warning("[odds] API key inválida — desactivando provider hasta restart")
        os.environ.pop("EDGEBET_ODDS_API_KEY", None)
        return []
    if resp.status_code != 200:
        logger.warning("[odds] %s status=%s", league_slug, resp.status_code)
        return []

    try:
        data = resp.json()
    except ValueError:
        logger.warning("[odds] %s respuesta no-JSON", league_slug)
        return []

    out: list[dict] = []
    for game in data:
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        kickoff = game.get("commence_time", "")
        bookmakers = game.get("bookmakers", [])

        # Buscamos el primer bookmaker preferido con mercados completos.
        chosen = None
        for pref in PREFERRED_BOOKMAKERS:
            chosen = next((b for b in bookmakers if b.get("key") == pref), None)
            if chosen:
                break
        if chosen is None and bookmakers:
            chosen = bookmakers[0]
        if chosen is None:
            continue

        chosen["_home_lower"] = home_team.lower()
        chosen["_away_lower"] = away_team.lower()
        h, d, a = _extract_h2h(chosen)
        over, under = _extract_totals(chosen, 2.5)

        out.append({
            "home_team": home_team,
            "away_team": away_team,
            "kickoff": kickoff,
            "bookmaker": chosen.get("key"),
            "h2h": {"home": h, "draw": d, "away": a},
            "totals_2_5": {"over": over, "under": under},
            "last_update": chosen.get("last_update"),
        })

    _write_cache(_cache_path(cache_key), out)

    # Persiste snapshot para análisis de movimientos. Solo si tenemos fixture.
    _persist_snapshots(league_slug, out)
    return out


def _persist_snapshots(league_slug: str, odds_list: list[dict]) -> None:
    """Match-up por nombre de equipo — si el fixture existe, agregamos snapshot."""
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
                fixture_id = row["id"]
                cur.execute("""
                    INSERT INTO odds_snapshots
                    (fixture_id, bookmaker, market, home_odds, draw_odds, away_odds, over_2_5_odds, under_2_5_odds)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    fixture_id, entry["bookmaker"], "h2h+totals",
                    entry["h2h"].get("home"), entry["h2h"].get("draw"), entry["h2h"].get("away"),
                    entry["totals_2_5"].get("over"), entry["totals_2_5"].get("under"),
                ))
    except Exception as exc:
        logger.warning("[odds] persist snapshot falló: %s", exc)


def find_odds_for_match(home_team: str, away_team: str, league_slug: str) -> Optional[dict]:
    """Busca odds reales para un match específico (case-insensitive, normaliza espacios)."""
    odds = fetch_league_odds(league_slug)
    if not odds:
        return None
    h_norm = home_team.strip().lower()
    a_norm = away_team.strip().lower()
    return next(
        (o for o in odds
         if o["home_team"].strip().lower() == h_norm
         and o["away_team"].strip().lower() == a_norm),
        None,
    )


def provider_status() -> dict:
    """Útil para /health y para que el frontend muestre estado del feed real."""
    return {
        "configured": is_configured(),
        "provider": "the-odds-api",
        "leagues_supported": list(SPORT_KEY_BY_LEAGUE.keys()),
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
    }
