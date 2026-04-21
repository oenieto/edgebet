"""
Edgebet — integración live con Polymarket Gamma API.

Busca el mercado de fútbol correspondiente a un (home, away) concreto y
devuelve probabilidades 3-way. Aplica matching difuso sobre los nombres,
cache con TTL para no abusar del endpoint, y tolera fallos silenciosamente.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from typing import Optional

GAMMA_API = "https://gamma-api.polymarket.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36"
)

FOOTBALL_KEYWORDS = [
    "soccer", "football match", "premier league", "la liga", "bundesliga",
    "serie a", "ligue 1", "champions league", "europa league", "uefa",
    "copa", "epl",
]

CACHE_TTL_SECONDS = 15 * 60


@dataclass
class PolymarketPick:
    home: float
    draw: float
    away: float
    liquidity: float
    volume_24h: float
    market_slug: str
    question: str
    confidence: float  # similitud 0-1 contra (home vs away)


_cache: dict[str, tuple[float, list[dict]]] = {}


def _normalize(name: str) -> str:
    s = name.lower()
    s = re.sub(r"\b(fc|cf|sc|afc|club|ac|rcd|ssc|us|as)\b", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _contains_teams(text: str, home: str, away: str) -> float:
    """Heurística: devuelve score 0-1 si la pregunta menciona ambos equipos."""
    n_text = _normalize(text)
    n_home = _normalize(home)
    n_away = _normalize(away)
    if not n_home or not n_away:
        return 0.0

    home_hit = 1.0 if n_home in n_text else _similarity(n_home, n_text)
    away_hit = 1.0 if n_away in n_text else _similarity(n_away, n_text)

    # Si la pregunta contiene los 2 equipos con alta similitud → confianza alta
    if n_home in n_text and n_away in n_text:
        return 0.95
    return (home_hit + away_hit) / 2.0


def _fetch_json(url: str, params: dict | None = None, timeout: int = 15):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _fetch_active_football_markets(max_items: int = 200) -> list[dict]:
    """Descarga los mercados activos y filtra los relacionados con fútbol."""
    now = time.time()
    if "active" in _cache:
        ts, data = _cache["active"]
        if now - ts < CACHE_TTL_SECONDS:
            return data

    markets: list[dict] = []
    offset = 0
    try:
        while offset < max_items:
            page = _fetch_json(
                f"{GAMMA_API}/markets",
                params={"active": "true", "closed": "false", "limit": 50, "offset": offset},
            )
            if not isinstance(page, list) or not page:
                break
            for m in page:
                text = (m.get("question", "") + " " + (m.get("description", "") or "")).lower()
                if any(kw in text for kw in FOOTBALL_KEYWORDS):
                    markets.append(m)
            offset += 50
            time.sleep(0.4)  # rate-limit cortés
    except Exception as exc:
        print(f"[polymarket_live] fallo fetch: {exc}")

    _cache["active"] = (now, markets)
    return markets


def _extract_probs(market: dict) -> Optional[dict]:
    try:
        outcomes = market.get("outcomes") or []
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        prices_raw = market.get("outcomePrices") or "[]"
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        prices = [float(p) for p in prices]
        outcomes_lower = [str(o).lower() for o in outcomes]

        if len(prices) == 2:
            # Mercado binario: asumimos outcome[0] = equipo nombrado
            return {"home": prices[0], "draw": None, "away": prices[1]}
        if len(prices) >= 3:
            home_idx = next((i for i, o in enumerate(outcomes_lower) if "home" in o or "win" in o or "1" == o), 0)
            draw_idx = next((i for i, o in enumerate(outcomes_lower) if "draw" in o or "tie" in o or "x" == o), 1)
            away_idx = next((i for i, o in enumerate(outcomes_lower) if "away" in o or "lose" in o or "2" == o), 2)
            return {
                "home": prices[home_idx],
                "draw": prices[draw_idx],
                "away": prices[away_idx],
            }
    except Exception as exc:
        print(f"[polymarket_live] extract_probs error: {exc}")
    return None


def find_match_probs(home_team: str, away_team: str, min_confidence: float = 0.55) -> Optional[PolymarketPick]:
    """
    Devuelve las probs 3-way de Polymarket para home vs away, o None si
    no hay mercado confiable. Normaliza empates sintéticos si el mercado
    es binario.
    """
    markets = _fetch_active_football_markets()
    if not markets:
        return None

    best: Optional[tuple[float, dict, dict]] = None
    for m in markets:
        text = m.get("question", "") + " " + (m.get("description", "") or "")
        score = _contains_teams(text, home_team, away_team)
        if score < min_confidence:
            continue
        probs = _extract_probs(m)
        if not probs:
            continue
        if best is None or score > best[0]:
            best = (score, m, probs)

    if not best:
        return None

    score, market, probs = best

    # Si es binario, inferimos empate proporcional
    home = probs["home"] or 0.0
    away = probs["away"] or 0.0
    draw = probs["draw"]
    if draw is None:
        # Mercado binario: distribuimos ~25% a empate ajustando el resto
        base_draw = 0.25
        scale = max(home + away, 1e-6)
        home_n = (home / scale) * (1 - base_draw)
        away_n = (away / scale) * (1 - base_draw)
        home, draw, away = home_n, base_draw, away_n

    # Renormalizar
    total = home + draw + away
    if total <= 0:
        return None
    home /= total
    draw /= total
    away /= total

    return PolymarketPick(
        home=round(float(home), 4),
        draw=round(float(draw), 4),
        away=round(float(away), 4),
        liquidity=float(market.get("liquidity") or 0),
        volume_24h=float(market.get("volume24hr") or 0),
        market_slug=market.get("slug") or "",
        question=market.get("question") or "",
        confidence=round(float(score), 3),
    )


def find_match_probs_as_dict(home_team: str, away_team: str) -> Optional[dict]:
    pick = find_match_probs(home_team, away_team)
    if not pick:
        return None
    return asdict(pick)
