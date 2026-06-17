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

# Tier del Odds API. Free: solo h2h/spreads/totals. Starter+: añadimos mercados
# adicionales (alternate_totals, btts, double_chance, draw_no_bet, team_totals).
# Cambiar via env `EDGEBET_ODDS_TIER=free|starter|pro`.
TIER_MARKETS = {
    "free": "h2h,spreads,totals",
    "starter": "h2h,spreads,totals,alternate_totals,btts,double_chance,draw_no_bet,team_totals",
    "pro": "h2h,spreads,totals,alternate_totals,alternate_spreads,btts,double_chance,draw_no_bet,team_totals,team_totals_alternate",
}


def _markets_for_tier() -> str:
    tier = (os.environ.get("EDGEBET_ODDS_TIER") or "free").lower()
    return TIER_MARKETS.get(tier, TIER_MARKETS["free"])


# Normalización de nombres del Odds API a nuestras formas canónicas.
# El Odds API usa "Pumas" sin UNAM, "Club America" en lugar de "America", etc.
# Mantener sincronizado con `_NAME_OVERRIDES` en openfootball_loader.py.
_ODDS_API_TEAM_OVERRIDES = {
    # Liga MX
    "Pumas": "Pumas UNAM",
    "Pumas UNAM": "Pumas UNAM",
    "Club America": "America",
    "America": "America",
    "Club Necaxa": "Necaxa",
    "Necaxa": "Necaxa",
    "Tigres": "Tigres UANL",
    "Tigres UANL": "Tigres UANL",
    "Club Leon": "Leon",
    "Leon": "Leon",
    "FC Juarez": "Juarez",
    "Juarez": "Juarez",
    "Queretaro FC": "Queretaro",
    "Queretaro": "Queretaro",
    "Guadalajara Chivas": "Guadalajara",
    "Atlas FC": "Atlas",
    "Mazatlan FC": "Mazatlan",
    "Atletico San Luis": "Atletico San Luis",
}


def _normalize_odds_team(name: str) -> str:
    if not name:
        return name
    return _ODDS_API_TEAM_OVERRIDES.get(name, name)


SPORT_KEY_BY_LEAGUE = {
    "premier-league": "soccer_epl",
    "la-liga": "soccer_spain_la_liga",
    "bundesliga": "soccer_germany_bundesliga",
    "serie-a": "soccer_italy_serie_a",
    "ligue-1": "soccer_france_ligue_one",
    "champions-league": "soccer_uefa_champs_league",
    "liga-mx": "soccer_mexico_ligamx",
    "fifa-world-cup": "soccer_fifa_world_cup",
}

# Bookmakers preferidos — orden de prioridad para extraer odds canónicos.
PREFERRED_BOOKMAKERS = ("pinnacle", "bet365", "williamhill", "unibet", "draftkings")

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
# Cache largo a propósito: el tier free son 500 req/mes. Con 6 ligas
# polleadas cada 5 min se quema en horas. 45 min da margen para ~960 req/mes
# en steady state (mucho debajo del cap). Las cuotas se mueven pero no tanto
# como para invalidar EV en 45 min — los picks no son arbitraje, son edges.
# Override vía env `EDGEBET_ODDS_CACHE_SECONDS` cuando subas a paid tier.
CACHE_TTL_SECONDS = int(os.environ.get("EDGEBET_ODDS_CACHE_SECONDS", str(60 * 45)))
REQUEST_TIMEOUT = 6

# Circuit breaker: cuando recibimos 401 (cuota agotada del tier free),
# congelamos llamadas al provider por este intervalo. Después auto-reintentamos
# por si la cuota mensual ya se reseteó o el plan se actualizó. Sin esto cada
# request al dashboard hace 6 round-trips a la API para recibir 6 × 401.
QUOTA_EXHAUSTED_COOLDOWN_SECONDS = 30 * 60  # 30 min
_quota_exhausted_until: float = 0.0

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


def _read_cache_stale(path: Path) -> Optional[dict]:
    """Lee el cache aunque haya expirado — para fallback cuando el API falla."""
    if not path.exists():
        return None
    try:
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


def _extract_all_totals(bookmaker_block: dict) -> dict[str, dict[str, float]]:
    """
    Extrae TODAS las líneas de totals que devuelva el bookmaker.
    Retorna dict {"1.5": {"over": 1.20, "under": 4.50}, "2.5": {...}, ...}.
    """
    totals = next((m for m in bookmaker_block.get("markets", []) if m.get("key") == "totals"), None)
    if not totals:
        return {}
    lines: dict[str, dict[str, float]] = {}
    for o in totals.get("outcomes", []):
        point = o.get("point")
        if point is None:
            continue
        key = f"{float(point):.1f}"
        name = (o.get("name") or "").lower()
        price = o.get("price")
        if price is None:
            continue
        lines.setdefault(key, {})
        if name == "over":
            lines[key]["over"] = float(price)
        elif name == "under":
            lines[key]["under"] = float(price)
    return {k: v for k, v in lines.items() if "over" in v and "under" in v}


def _extract_spreads(bookmaker_block: dict) -> dict[str, dict[str, float]]:
    """
    Extrae handicaps (spreads) por punto. Retorna dict por línea:
    {"-1.5": {"home": 3.20, "away": 1.36}, "+1.5": {...}, ...}
    El "home" siempre lleva el handicap mostrado; "away" recibe el opuesto
    automáticamente (lo da el provider en outcomes separados).
    """
    spreads = next((m for m in bookmaker_block.get("markets", []) if m.get("key") == "spreads"), None)
    if not spreads:
        return {}
    home_lower = bookmaker_block.get("_home_lower", "")
    lines: dict[str, dict[str, float]] = {}
    for o in spreads.get("outcomes", []):
        point = o.get("point")
        if point is None:
            continue
        name = (o.get("name") or "").lower()
        price = o.get("price")
        if price is None:
            continue
        # Usar el punto desde la perspectiva del home — si este outcome es del
        # home, el point ya lo expresa así. Si es del away, le damos vuelta.
        is_home = name == home_lower
        line_key = f"{float(point):+.1f}" if is_home else f"{-float(point):+.1f}"
        lines.setdefault(line_key, {})
        if is_home:
            lines[line_key]["home"] = float(price)
        else:
            lines[line_key]["away"] = float(price)
    return {k: v for k, v in lines.items() if "home" in v and "away" in v}


def _aggregate_totals_across_books(bookmakers: list[dict]) -> dict[str, dict[str, float]]:
    """
    Junta todas las líneas de totals que ofrece CADA bookmaker, quedándose
    con la MEJOR cuota para el apostador (mayor odds) en over y under
    por separado. Esto saca el máximo provecho del tier free porque cada
    casa ofrece líneas distintas (algunas dan 1.5, otras 2.5, otras 3.5).
    """
    best: dict[str, dict[str, float]] = {}
    for bk in bookmakers:
        lines = _extract_all_totals(bk)
        for line_key, prices in lines.items():
            entry = best.setdefault(line_key, {})
            for side in ("over", "under"):
                if side in prices and prices[side] > entry.get(side, 0):
                    entry[side] = prices[side]
                    entry[f"{side}_bookmaker"] = bk.get("key")
    return best


def _aggregate_spreads_across_books(bookmakers: list[dict], home_lower: str) -> dict[str, dict[str, float]]:
    """Misma idea que totals — best price por handicap line desde el set de bookies."""
    best: dict[str, dict[str, float]] = {}
    for bk in bookmakers:
        bk["_home_lower"] = home_lower
        lines = _extract_spreads(bk)
        for line_key, prices in lines.items():
            entry = best.setdefault(line_key, {})
            for side in ("home", "away"):
                if side in prices and prices[side] > entry.get(side, 0):
                    entry[side] = prices[side]
                    entry[f"{side}_bookmaker"] = bk.get("key")
    return best


def derive_double_chance_odds(
    h: float | None, d: float | None, a: float | None
) -> dict[str, float] | None:
    """
    Deriva cuotas DC desde h2h aplicando el margen del propio bookmaker.

    Matemáticamente: p_implied(1X) = 1/h + 1/d. La cuota DC justa = 1 / p_implied(1X).
    Esto preserva el margen total del bookmaker en h2h, lo cual es una
    aproximación cercana a cómo realmente cotizan DC (margen DC suele ser
    ~1-2pp menor, pero la diferencia para EV es marginal).
    """
    if h is None or d is None or a is None:
        return None
    if h <= 1.0 or d <= 1.0 or a <= 1.0:
        return None
    inv_h, inv_d, inv_a = 1.0 / h, 1.0 / d, 1.0 / a
    return {
        "1X": round(1.0 / (inv_h + inv_d), 2),
        "X2": round(1.0 / (inv_d + inv_a), 2),
        "12": round(1.0 / (inv_h + inv_a), 2),
    }


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

    # Circuit breaker: si ya sabemos que la cuota está exhausta, ni intentamos.
    # Servimos directamente el cache stale para que el dashboard siga vivo.
    global _quota_exhausted_until
    now = time.time()
    if now < _quota_exhausted_until:
        stale = _read_cache_stale(_cache_path(cache_key))
        return stale if stale else []

    url = f"{API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": _api_key(),
        "regions": "eu,uk,us",
        "markets": _markets_for_tier(),
        "oddsFormat": "decimal",
    }
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        logger.warning("[odds] %s red falló: %s — usando cache stale", league_slug, exc)
        stale = _read_cache_stale(_cache_path(cache_key))
        return stale if stale else []

    if resp.status_code == 401:
        # Cuota agotada del tier free. Activamos circuit breaker para no
        # gastar el último request restante en los próximos 30 min, y servimos
        # cache stale. Auto-reintenta cuando expire el cooldown.
        _quota_exhausted_until = now + QUOTA_EXHAUSTED_COOLDOWN_SECONDS
        logger.warning(
            "[odds] %s 401 (cuota agotada) — circuit breaker activo %d min, usando cache stale",
            league_slug,
            QUOTA_EXHAUSTED_COOLDOWN_SECONDS // 60,
        )
        stale = _read_cache_stale(_cache_path(cache_key))
        return stale if stale else []
    if resp.status_code != 200:
        logger.warning("[odds] %s status=%s — usando cache stale", league_slug, resp.status_code)
        stale = _read_cache_stale(_cache_path(cache_key))
        return stale if stale else []

    try:
        data = resp.json()
    except ValueError:
        logger.warning("[odds] %s respuesta no-JSON", league_slug)
        return []

    out: list[dict] = []
    for game in data:
        home_team = _normalize_odds_team(game.get("home_team", ""))
        away_team = _normalize_odds_team(game.get("away_team", ""))
        home_lower = (game.get("home_team", "") or "").lower()
        kickoff = game.get("commence_time", "")
        bookmakers = game.get("bookmakers", [])

        # Bookmaker primario — el primero preferido con h2h disponible.
        # Lo usamos como referencia para h2h "canónico" (necesario para DC
        # derivado y el pick ML). Los demás mercados se agregan cross-book.
        chosen = None
        for pref in PREFERRED_BOOKMAKERS:
            chosen = next((b for b in bookmakers if b.get("key") == pref), None)
            if chosen:
                break
        if chosen is None and bookmakers:
            chosen = bookmakers[0]
        if chosen is None:
            continue

        chosen["_home_lower"] = home_lower
        chosen["_away_lower"] = (game.get("away_team", "") or "").lower()
        h, d, a = _extract_h2h(chosen)
        dc_derived = derive_double_chance_odds(h, d, a)

        # Agregaciones cross-bookmaker: best price disponible para cada línea.
        # Esto saca máximo provecho del free tier porque cada casa expone
        # líneas distintas de totals/spreads.
        totals_by_line = _aggregate_totals_across_books(bookmakers)
        spreads_by_line = _aggregate_spreads_across_books(bookmakers, home_lower)

        # Mantenemos totals_2_5 por retro-compatibilidad con persist_snapshots
        totals_2_5 = totals_by_line.get("2.5", {})

        out.append({
            "home_team": home_team,
            "away_team": away_team,
            "kickoff": kickoff,
            "bookmaker": chosen.get("key"),
            "h2h": {"home": h, "draw": d, "away": a},
            "totals_2_5": {"over": totals_2_5.get("over"), "under": totals_2_5.get("under")},
            "totals_by_line": totals_by_line,
            "spreads_by_line": spreads_by_line,
            "double_chance": dc_derived,
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
