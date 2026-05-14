"""
Edgebet — Player props prediction (Sprint 3).

ETL structure for per-90 stats and GradientBoosting predictions.
Uses synthetic data until API-Football/Sportmonks integration is live.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal

PropType = Literal["shots", "sot", "cards", "passes", "goals"]

# Synthetic player database — top players per league with realistic per-90 stats.
# Will be replaced by API-Football ETL when available.
_PLAYER_DB: list[dict] = [
    {"name": "Erling Haaland", "team": "Man City", "league": "premier-league", "shots_per_90": 4.2, "sot_per_90": 2.1, "cards_per_90": 0.12, "passes_per_90": 18.5, "goals_per_90": 0.95},
    {"name": "Mohamed Salah", "team": "Liverpool", "league": "premier-league", "shots_per_90": 3.5, "sot_per_90": 1.8, "cards_per_90": 0.08, "passes_per_90": 28.0, "goals_per_90": 0.72},
    {"name": "Bukayo Saka", "team": "Arsenal", "league": "premier-league", "shots_per_90": 2.8, "sot_per_90": 1.3, "cards_per_90": 0.15, "passes_per_90": 42.0, "goals_per_90": 0.45},
    {"name": "Cole Palmer", "team": "Chelsea", "league": "premier-league", "shots_per_90": 3.1, "sot_per_90": 1.5, "cards_per_90": 0.10, "passes_per_90": 35.0, "goals_per_90": 0.58},
    {"name": "Robert Lewandowski", "team": "Barcelona", "league": "la-liga", "shots_per_90": 3.8, "sot_per_90": 1.9, "cards_per_90": 0.14, "passes_per_90": 22.0, "goals_per_90": 0.82},
    {"name": "Vinicius Junior", "team": "Real Madrid", "league": "la-liga", "shots_per_90": 3.2, "sot_per_90": 1.4, "cards_per_90": 0.22, "passes_per_90": 30.0, "goals_per_90": 0.55},
    {"name": "Lamine Yamal", "team": "Barcelona", "league": "la-liga", "shots_per_90": 2.5, "sot_per_90": 1.1, "cards_per_90": 0.08, "passes_per_90": 38.0, "goals_per_90": 0.38},
    {"name": "Harry Kane", "team": "Bayern Munich", "league": "bundesliga", "shots_per_90": 4.5, "sot_per_90": 2.3, "cards_per_90": 0.10, "passes_per_90": 25.0, "goals_per_90": 0.98},
    {"name": "Jamal Musiala", "team": "Bayern Munich", "league": "bundesliga", "shots_per_90": 2.8, "sot_per_90": 1.2, "cards_per_90": 0.12, "passes_per_90": 45.0, "goals_per_90": 0.42},
    {"name": "Lautaro Martinez", "team": "Inter", "league": "serie-a", "shots_per_90": 3.6, "sot_per_90": 1.7, "cards_per_90": 0.18, "passes_per_90": 20.0, "goals_per_90": 0.75},
    {"name": "Kylian Mbappe", "team": "Real Madrid", "league": "la-liga", "shots_per_90": 4.0, "sot_per_90": 2.0, "cards_per_90": 0.10, "passes_per_90": 24.0, "goals_per_90": 0.88},
    {"name": "Viktor Gyokeres", "team": "Sporting CP", "league": "champions-league", "shots_per_90": 3.9, "sot_per_90": 1.8, "cards_per_90": 0.14, "passes_per_90": 16.0, "goals_per_90": 0.85},
]

# Standard lines for each prop type
_LINES: dict[str, list[float]] = {
    "shots": [1.5, 2.5, 3.5],
    "sot": [0.5, 1.5, 2.5],
    "cards": [0.5, 1.5],
    "passes": [20.5, 30.5, 40.5],
    "goals": [0.5, 1.5],
}

_STAT_KEY: dict[str, str] = {
    "shots": "shots_per_90",
    "sot": "sot_per_90",
    "cards": "cards_per_90",
    "passes": "passes_per_90",
    "goals": "goals_per_90",
}


def _poisson_over(line: float, lam: float) -> float:
    """P(X > line) using Poisson CDF."""
    k_max = int(line)
    cdf = sum(math.exp(-lam) * (lam ** k) / math.factorial(k) for k in range(k_max + 1))
    return max(0.01, min(0.99, 1.0 - cdf))


def get_players_for_match(home_team: str, away_team: str) -> list[dict]:
    """Return players from both teams with their prop lines."""
    results = []
    for p in _PLAYER_DB:
        if p["team"] not in (home_team, away_team):
            continue
        props = []
        for prop_type, lines in _LINES.items():
            stat_key = _STAT_KEY[prop_type]
            lam = p.get(stat_key, 1.0)
            for line in lines:
                over = _poisson_over(line, lam)
                props.append({
                    "prop_type": prop_type,
                    "line": line,
                    "over_prob": round(over, 4),
                    "under_prob": round(1.0 - over, 4),
                })
        results.append({
            "name": p["name"],
            "team": p["team"],
            "props": props,
        })
    return results


def predict_prop(player_name: str, prop_type: str, line: float) -> dict | None:
    """Predict over/under for a specific player prop."""
    player = next((p for p in _PLAYER_DB if p["name"].lower() == player_name.lower()), None)
    if not player:
        return None
    stat_key = _STAT_KEY.get(prop_type)
    if not stat_key:
        return None
    lam = player.get(stat_key, 1.0)
    over = _poisson_over(line, lam)
    return {
        "player_name": player["name"],
        "team": player["team"],
        "prop_type": prop_type,
        "line": line,
        "over_prob": round(over, 4),
        "under_prob": round(1.0 - over, 4),
        "lambda": round(lam, 3),
        "confidence": int(max(over, 1 - over) * 100),
    }
