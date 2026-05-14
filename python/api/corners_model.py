"""
Edgebet — corners prediction model (Sprint 2).

Poisson-based model for total match corners. Uses avg corners per team
+ possession/shots adjustments. No numpy/sklearn dependency — pure math.

Will be replaced by a trained Random Forest when real per-match corner
data is available from API-Football or Sportmonks.
"""
from __future__ import annotations

import math

# League average corners per team per match (Big 5 average 2024/25)
LEAGUE_AVG_CORNERS = 5.2
HOME_CORNER_BOOST = 0.4  # Home teams average ~0.4 more corners


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _poisson_over(line: float, lam: float) -> float:
    """P(X > line) for Poisson(lam)."""
    k_max = int(line)
    cdf = sum(_poisson_pmf(k, lam) for k in range(k_max + 1))
    return max(0.01, min(0.99, 1.0 - cdf))


def predict_corners(home_form: dict, away_form: dict) -> dict:
    """
    Predict corner totals for a match.

    Returns dict with over/under probabilities for 9.5 and 10.5 lines,
    plus expected total corners.
    """
    home_avg = max(0.5, float(home_form.get("avg_Corners", LEAGUE_AVG_CORNERS)))
    away_avg = max(0.5, float(away_form.get("avg_Corners", LEAGUE_AVG_CORNERS - 0.5)))

    # Possession adjustment: teams with more possession tend to get more corners
    home_poss = float(home_form.get("possession", 50)) / 100
    away_poss = float(away_form.get("possession", 50)) / 100

    # Lambda per team
    lam_home = home_avg * (1 + (home_poss - 0.5) * 0.3) + HOME_CORNER_BOOST
    lam_away = away_avg * (1 + (away_poss - 0.5) * 0.3)

    lam_total = max(1.0, lam_home + lam_away)

    return {
        "over_9_5": round(_poisson_over(9.5, lam_total), 4),
        "under_9_5": round(1 - _poisson_over(9.5, lam_total), 4),
        "over_10_5": round(_poisson_over(10.5, lam_total), 4),
        "under_10_5": round(1 - _poisson_over(10.5, lam_total), 4),
        "expected_corners": round(lam_total, 1),
        "lambda_home": round(lam_home, 2),
        "lambda_away": round(lam_away, 2),
    }
