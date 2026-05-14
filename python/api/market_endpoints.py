"""
Edgebet — Market-specific pick endpoints (Sprint 2).

Generates picks for BTTS, Corners, and Asian Handicap markets
using the existing picks pipeline + specialized models.
"""
from __future__ import annotations

from uuid import uuid4

from api.picks_service import get_todays_picks, _load_league, LEAGUES
from api.btts_model import predict_btts
from api.corners_model import predict_corners
from api.fast_loader import compute_team_form


def _base_pick_fields(pick: dict) -> dict:
    """Extract common fields from a 1X2 pick to reuse in market picks."""
    return {
        "homeTeam": pick["homeTeam"],
        "awayTeam": pick["awayTeam"],
        "homeLogo": pick.get("homeLogo"),
        "awayLogo": pick.get("awayLogo"),
        "league": pick["league"],
        "leagueSlug": pick.get("leagueSlug"),
        "kickoff": pick["kickoff"],
        "odds": pick.get("odds"),
        "modelSource": "specialized",
    }


def get_btts_picks(league_slug: str | None = None) -> list[dict]:
    """BTTS picks derived from today's 1X2 pool + BTTS model."""
    base_picks = get_todays_picks(league_slug=league_slug)
    results = []

    for pick in base_picks:
        slug = pick.get("leagueSlug")
        if not slug or slug not in LEAGUES:
            continue
        try:
            matches, ratings, cfg = _load_league(slug)
            home_form = compute_team_form(matches, pick["homeTeam"])
            away_form = compute_team_form(matches, pick["awayTeam"])
            btts = predict_btts(home_form, away_form)
        except Exception:
            continue

        prediction = "btts_yes" if btts["btts_yes"] > btts["btts_no"] else "btts_no"
        confidence = btts["confidence"]
        prob = max(btts["btts_yes"], btts["btts_no"])

        results.append({
            "id": str(uuid4()),
            "match": pick["match"],
            **_base_pick_fields(pick),
            "market": "BTTS",
            "prediction": prediction,
            "confidence": confidence,
            "mlProb": {"btts_yes": btts["btts_yes"], "btts_no": btts["btts_no"]},
            "bkProb": pick.get("bkProb", {}),
            "polyProb": None,
            "blendedProb": {"btts_yes": btts["btts_yes"], "btts_no": btts["btts_no"]},
            "aiReasoning": f"BTTS {'Si' if prediction == 'btts_yes' else 'No'} con {confidence}% confianza. "
                          f"Basado en promedios de goles y porcentaje de clean sheets.",
            "suggestedStake": round(max(0, (prob - 0.55) * 20), 1),
            "status": "premium" if confidence >= 65 else "free",
            "edgePp": None,
            "evPct": None,
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def get_corners_picks(league_slug: str | None = None) -> list[dict]:
    """Corners O/U picks derived from today's pool + corners model."""
    base_picks = get_todays_picks(league_slug=league_slug)
    results = []

    for pick in base_picks:
        slug = pick.get("leagueSlug")
        if not slug or slug not in LEAGUES:
            continue
        try:
            matches, ratings, cfg = _load_league(slug)
            home_form = compute_team_form(matches, pick["homeTeam"])
            away_form = compute_team_form(matches, pick["awayTeam"])
            corners = predict_corners(home_form, away_form)
        except Exception:
            continue

        # Pick the strongest corner line
        best_outcome = "over_9_5"
        best_prob = corners["over_9_5"]
        for key in ("under_9_5", "over_10_5", "under_10_5"):
            if corners[key] > best_prob:
                best_prob = corners[key]
                best_outcome = key

        confidence = int(best_prob * 100)
        label_map = {
            "over_9_5": "Mas de 9.5 corners",
            "under_9_5": "Menos de 9.5 corners",
            "over_10_5": "Mas de 10.5 corners",
            "under_10_5": "Menos de 10.5 corners",
        }

        results.append({
            "id": str(uuid4()),
            "match": pick["match"],
            **_base_pick_fields(pick),
            "market": "CORNERS",
            "prediction": best_outcome,
            "confidence": confidence,
            "mlProb": corners,
            "bkProb": {},
            "polyProb": None,
            "blendedProb": corners,
            "aiReasoning": f"{label_map.get(best_outcome, best_outcome)} ({confidence}%). "
                          f"Total esperado: {corners['expected_corners']:.1f} corners.",
            "suggestedStake": round(max(0, (best_prob - 0.55) * 15), 1),
            "status": "premium" if confidence >= 60 else "free",
            "edgePp": None,
            "evPct": None,
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def get_ah_picks(league_slug: str | None = None) -> list[dict]:
    """
    Asian Handicap picks — calibrated spread via 1X2 probabilities.
    AH -0.5 = ML win. AH -1.5 = win by 2+ goals. etc.
    """
    base_picks = get_todays_picks(league_slug=league_slug)
    results = []

    for pick in base_picks:
        blended = pick.get("blendedProb", {})
        home_prob = blended.get("home", 0.33)
        away_prob = blended.get("away", 0.33)

        # Derive AH spreads from 1X2 probs
        # AH -0.5 home ≈ P(home win)
        # AH -1.5 home ≈ P(home win) * 0.6 (rough calibration)
        # AH +0.5 away ≈ P(away win) + P(draw)
        ah_lines = []
        ah_lines.append({
            "line": "home -0.5",
            "prob": round(home_prob, 4),
            "label": f"{pick['homeTeam']} -0.5",
        })
        ah_lines.append({
            "line": "home -1.5",
            "prob": round(home_prob * 0.58, 4),
            "label": f"{pick['homeTeam']} -1.5",
        })
        ah_lines.append({
            "line": "away +0.5",
            "prob": round(1.0 - home_prob, 4),
            "label": f"{pick['awayTeam']} +0.5",
        })
        ah_lines.append({
            "line": "away -0.5",
            "prob": round(away_prob, 4),
            "label": f"{pick['awayTeam']} -0.5",
        })

        best = max(ah_lines, key=lambda x: x["prob"])
        confidence = int(best["prob"] * 100)

        results.append({
            "id": str(uuid4()),
            "match": pick["match"],
            **_base_pick_fields(pick),
            "market": "AH",
            "prediction": best["line"],
            "confidence": confidence,
            "mlProb": {l["line"]: l["prob"] for l in ah_lines},
            "bkProb": pick.get("bkProb", {}),
            "polyProb": None,
            "blendedProb": {l["line"]: l["prob"] for l in ah_lines},
            "aiReasoning": f"Handicap Asiatico: {best['label']} con {confidence}% probabilidad. "
                          f"Derivado del modelo 1X2 calibrado.",
            "suggestedStake": round(max(0, (best["prob"] - 0.55) * 18), 1),
            "status": "premium" if confidence >= 60 else "free",
            "edgePp": None,
            "evPct": None,
            "ahLines": ah_lines,
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results
