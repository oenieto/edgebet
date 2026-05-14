"""
Edgebet — xG provider.

Sprint 1 Antonio: Replaces the SoT*0.30 + (Shots-SoT)*0.03 proxy with real
xG values scraped from Understat (free, no API key required).

Public API
----------
get_team_xg(team_name, season) -> {"xg_for": float, "xg_against": float, "npxg": float}

Falls back to the old proxy automatically when scraping fails.
Cache TTL: 1 hour (in-process).
"""
from __future__ import annotations

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Team-name → Understat slug mapping
# Understat uses its own spelling. Add / extend as needed.
# ---------------------------------------------------------------------------
UNDERSTAT_SLUGS: dict[str, str] = {
    # Premier League
    "Manchester City": "Manchester_City",
    "Man City": "Manchester_City",
    "Manchester United": "Manchester_United",
    "Man United": "Manchester_United",
    "Man Utd": "Manchester_United",
    "Arsenal": "Arsenal",
    "Chelsea": "Chelsea",
    "Liverpool": "Liverpool",
    "Tottenham": "Tottenham",
    "Tottenham Hotspur": "Tottenham",
    "Newcastle": "Newcastle_United",
    "Newcastle United": "Newcastle_United",
    "Aston Villa": "Aston_Villa",
    "West Ham": "West_Ham",
    "West Ham United": "West_Ham",
    "Brighton": "Brighton",
    "Brentford": "Brentford",
    "Fulham": "Fulham",
    "Wolves": "Wolverhampton_Wanderers",
    "Wolverhampton": "Wolverhampton_Wanderers",
    "Crystal Palace": "Crystal_Palace",
    "Everton": "Everton",
    "Nottingham Forest": "Nottingham_Forest",
    "Bournemouth": "Bournemouth",
    "Leicester": "Leicester",
    "Leicester City": "Leicester",
    "Ipswich": "Ipswich",
    "Southampton": "Southampton",
    # La Liga
    "Barcelona": "Barcelona",
    "Real Madrid": "Real_Madrid",
    "Atletico Madrid": "Atletico_Madrid",
    "Atletico de Madrid": "Atletico_Madrid",
    "Athletic Bilbao": "Athletic_Club",
    "Athletic Club": "Athletic_Club",
    "Real Sociedad": "Real_Sociedad",
    "Real Betis": "Betis",
    "Villarreal": "Villarreal",
    "Valencia": "Valencia",
    "Sevilla": "Sevilla",
    "Getafe": "Getafe",
    "Rayo Vallecano": "Rayo_Vallecano",
    "Osasuna": "Osasuna",
    "Celta Vigo": "Celta_Vigo",
    "Las Palmas": "Las_Palmas",
    "Girona": "Girona",
    "Alaves": "Alaves",
    "Leganes": "Leganes",
    "Mallorca": "Mallorca",
    "Espanyol": "Espanyol",
    "Valladolid": "Valladolid",
    # Bundesliga
    "Bayern Munich": "Bayern",
    "Bayern": "Bayern",
    "Bayer Leverkusen": "Bayer_Leverkusen",
    "Borussia Dortmund": "Dortmund",
    "Dortmund": "Dortmund",
    "RB Leipzig": "RasenBallsport_Leipzig",
    "Leipzig": "RasenBallsport_Leipzig",
    "Eintracht Frankfurt": "Eintracht_Frankfurt",
    "Freiburg": "Freiburg",
    "Wolfsburg": "Wolfsburg",
    "Stuttgart": "Stuttgart",
    "Borussia Monchengladbach": "Borussia_M_Gladbach",
    "Werder Bremen": "Werder_Bremen",
    "Hoffenheim": "Hoffenheim",
    "Augsburg": "Augsburg",
    "Union Berlin": "Union_Berlin",
    "Mainz": "Mainz",
    "Heidenheim": "Heidenheim",
    "Holstein Kiel": "Holstein_Kiel",
    "St. Pauli": "St_Pauli",
    # Serie A
    "Inter Milan": "Internazionale",
    "Inter": "Internazionale",
    "Internazionale": "Internazionale",
    "AC Milan": "Milan",
    "Milan": "Milan",
    "Juventus": "Juventus",
    "Napoli": "Napoli",
    "Roma": "Roma",
    "AS Roma": "Roma",
    "Lazio": "Lazio",
    "Atalanta": "Atalanta",
    "Fiorentina": "Fiorentina",
    "Bologna": "Bologna",
    "Torino": "Torino",
    "Udinese": "Udinese",
    "Cagliari": "Cagliari",
    "Genoa": "Genoa",
    "Verona": "Hellas_Verona",
    "Hellas Verona": "Hellas_Verona",
    "Empoli": "Empoli",
    "Parma": "Parma",
    "Venezia": "Venezia",
    "Como": "Como",
    "Lecce": "Lecce",
    "Monza": "Monza",
    # Ligue 1
    "Paris Saint-Germain": "Paris_Saint_Germain",
    "PSG": "Paris_Saint_Germain",
    "Marseille": "Marseille",
    "Lyon": "Lyon",
    "Monaco": "Monaco",
    "Lille": "Lille",
    "Nice": "Nice",
    "Lens": "Lens",
    "Rennes": "Rennes",
    "Strasbourg": "Strasbourg",
    "Brest": "Brest",
    "Reims": "Reims",
    "Nantes": "Nantes",
    "Toulouse": "Toulouse",
    "Montpellier": "Montpellier",
    "Saint-Etienne": "Saint_Etienne",
    "Angers": "Angers",
    "Auxerre": "Auxerre",
    "Le Havre": "Le_Havre",
    "Sainté": "Saint_Etienne",
}

# League code used in Understat URLs: /league/<LEAGUE>/<SEASON>
UNDERSTAT_LEAGUE_MAP: dict[str, str] = {
    "EPL": "EPL",
    "La Liga": "La_liga",
    "Bundesliga": "Bundesliga",
    "Serie A": "Serie_A",
    "Ligue 1": "Ligue_1",
    "RFPL": "RFPL",
}

# ---------------------------------------------------------------------------
# In-process cache:  slug -> (timestamp, result_dict)
# ---------------------------------------------------------------------------
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


def _is_cached(slug: str) -> bool:
    if slug not in _CACHE:
        return False
    ts, _ = _CACHE[slug]
    return (time.time() - ts) < _CACHE_TTL_SECONDS


def _get_cached(slug: str) -> dict:
    _, data = _CACHE[slug]
    return data


def _set_cache(slug: str, data: dict) -> None:
    _CACHE[slug] = (time.time(), data)


# ---------------------------------------------------------------------------
# Proxy fallback (original formula)
# ---------------------------------------------------------------------------

def _xg_proxy(sot: float, shots: float) -> float:
    sot = max(sot or 0.0, 0.0)
    shots = max(shots or 0.0, 0.0)
    return sot * 0.30 + max(shots - sot, 0.0) * 0.03


def _proxy_result(
    home_sot: float = 4.2,
    home_shots: float = 11.5,
    away_sot: float = 3.8,
    away_shots: float = 10.8,
) -> dict:
    """Return a proxy-based result when scraping is impossible."""
    return {
        "xg_for": round(_xg_proxy(home_sot, home_shots), 3),
        "xg_against": round(_xg_proxy(away_sot, away_shots), 3),
        "npxg": round(_xg_proxy(home_sot, home_shots) * 0.92, 3),
        "source": "proxy",
    }


# ---------------------------------------------------------------------------
# Understat scraper
# ---------------------------------------------------------------------------

def _resolve_slug(team_name: str) -> Optional[str]:
    """Maps a common team name to its Understat slug."""
    if team_name in UNDERSTAT_SLUGS:
        return UNDERSTAT_SLUGS[team_name]
    # Case-insensitive fallback
    lower = team_name.lower()
    for key, slug in UNDERSTAT_SLUGS.items():
        if key.lower() == lower:
            return slug
    return None


def _scrape_understat_team(slug: str, season: str) -> Optional[dict]:
    """
    Scrapes team-level xG aggregates from Understat's team page.

    Understat embeds match data as JSON inside a <script> tag:
      var datesData = JSON.parse('...');

    We extract that payload, sum xG for and against across all matches in
    the requested season, and return per-match averages.

    Returns None on any failure so the caller can fall back to the proxy.
    """
    try:
        import re
        import json
        import urllib.request

        url = f"https://understat.com/team/{slug}/{season}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Understat stores match data in a JS variable: var datesData = JSON.parse('...');
        pattern = r"var\s+datesData\s*=\s*JSON\.parse\('(.+?)'\)"
        match = re.search(pattern, html)
        if not match:
            logger.debug("[xg_provider] datesData not found for %s", slug)
            return None

        raw = match.group(1)
        # Unescape Unicode and special chars embedded in the JS string
        raw = raw.replace("\\'", "'").encode("utf-8").decode("unicode_escape")
        matches_data: list[dict] = json.loads(raw)

        total_xg_for = 0.0
        total_xg_against = 0.0
        total_npxg = 0.0
        n = 0

        for m in matches_data:
            # Only finished matches have real xG
            if m.get("isResult") is not True and str(m.get("isResult", "")).lower() != "true":
                continue
            try:
                xg_f = float(m.get("xG", {}).get("h") or m.get("xg") or 0.0)
                xg_a = float(m.get("xG", {}).get("a") or m.get("xga") or 0.0)
                npxg_f = float(m.get("npxG", {}).get("h") or m.get("npxg") or xg_f * 0.92)
            except (TypeError, ValueError, AttributeError):
                continue
            # Understat's per-match xG for this team — "h" when team is home, "a" when away
            side = m.get("side", "h")
            if side == "h":
                total_xg_for += xg_f
                total_xg_against += xg_a
                total_npxg += npxg_f
            else:
                total_xg_for += xg_a
                total_xg_against += xg_f
                total_npxg += float(m.get("npxG", {}).get("a") or xg_a * 0.92)
            n += 1

        if n == 0:
            return None

        return {
            "xg_for": round(total_xg_for / n, 3),
            "xg_against": round(total_xg_against / n, 3),
            "npxg": round(total_npxg / n, 3),
            "source": "understat",
            "matches_used": n,
        }

    except Exception as exc:
        logger.warning("[xg_provider] scrape failed for %s/%s: %s", slug, season, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_team_xg(
    team_name: str,
    season: str = "2024",
    *,
    home_sot: float = 4.2,
    home_shots: float = 11.5,
    away_sot: float = 3.8,
    away_shots: float = 10.8,
) -> dict:
    """
    Return per-match average xG for a team in the given season.

    Result dict keys:
      - xg_for    : float — avg xG scored per match
      - xg_against: float — avg xG conceded per match
      - npxg      : float — avg non-penalty xG per match
      - source    : "understat" | "proxy"

    When Understat scraping fails the proxy values are derived from the
    optional sot/shots kwargs (league averages by default).
    """
    slug = _resolve_slug(team_name)
    if slug is None:
        logger.debug("[xg_provider] no slug for '%s', using proxy", team_name)
        return _proxy_result(home_sot, home_shots, away_sot, away_shots)

    cache_key = f"{slug}_{season}"
    if _is_cached(cache_key):
        return _get_cached(cache_key)

    result = _scrape_understat_team(slug, season)
    if result is None:
        result = _proxy_result(home_sot, home_shots, away_sot, away_shots)

    _set_cache(cache_key, result)
    return result


def get_xg_proxy_only(sot: float, shots: float) -> float:
    """Convenience wrapper — returns the scalar proxy value."""
    return _xg_proxy(sot, shots)


def clear_cache() -> None:
    """Clears in-process cache. Useful in tests."""
    _CACHE.clear()
