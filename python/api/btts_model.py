"""
Edgebet — Both Teams To Score (BTTS) model (Sprint 2/3).

Uses Poisson-derived probabilities from team goal averages.
Enhanced with clean sheet % and xG when available.
No numpy/sklearn dependency — pure math.
"""
from __future__ import annotations

import math


LEAGUE_AVG_GF = 1.40  # goals per team per match average


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def predict_btts(home_form: dict, away_form: dict) -> dict:
    """
    Predict BTTS Yes/No probabilities.

    P(BTTS=Yes) = P(home scores >= 1) * P(away scores >= 1)
    using Poisson with lambda derived from GF/GA rolling averages.

    Returns {"btts_yes": float, "btts_no": float, "confidence": int}
    """
    home_gf = max(0.1, float(home_form.get("avg_GF", 1.3)))
    home_ga = max(0.1, float(home_form.get("avg_GA", 1.2)))
    away_gf = max(0.1, float(away_form.get("avg_GF", 1.1)))
    away_ga = max(0.1, float(away_form.get("avg_GA", 1.3)))

    # Lambda: attack of team * defensive weakness of opponent
    lam_home = home_gf * (away_ga / LEAGUE_AVG_GF) + 0.15  # home boost
    lam_away = away_gf * (home_ga / LEAGUE_AVG_GF)

    lam_home = max(0.15, lam_home)
    lam_away = max(0.15, lam_away)

    # P(team scores at least 1) = 1 - P(team scores 0) = 1 - e^(-lambda)
    p_home_scores = 1.0 - math.exp(-lam_home)
    p_away_scores = 1.0 - math.exp(-lam_away)

    # P(BTTS) = P(home >= 1) * P(away >= 1) under independence
    btts_yes = p_home_scores * p_away_scores

    # Adjust with clean sheet data if available
    home_cs = float(home_form.get("clean_sheet_pct", 0))
    away_cs = float(away_form.get("clean_sheet_pct", 0))
    if home_cs > 0 or away_cs > 0:
        # Blend Poisson estimate with observed clean sheet rates
        cs_based_btts_no = 1 - (1 - home_cs) * (1 - away_cs)
        btts_yes = 0.7 * btts_yes + 0.3 * (1 - cs_based_btts_no)

    btts_yes = max(0.05, min(0.95, btts_yes))
    btts_no = 1.0 - btts_yes

    # Try to enhance with real xG
    try:
        from api.xg_provider import get_team_xg
        # If real xG available, blend it in
        # (currently a no-op until xG data is populated)
    except ImportError:
        pass

    confidence = int(max(btts_yes, btts_no) * 100)

    return {
        "btts_yes": round(btts_yes, 4),
        "btts_no": round(btts_no, 4),
        "confidence": confidence,
        "lambda_home": round(lam_home, 3),
        "lambda_away": round(lam_away, 3),
    }
