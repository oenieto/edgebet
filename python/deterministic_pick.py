"""
Edgebet — generador de picks determinista (sin Claude).

Lógica:
1. Compara nuestras probabilidades (ML/ELO) vs las implícitas del bookie.
2. Calcula EV por resultado: EV = p_nuestra * odds - 1.
3. Elige el outcome con mayor EV si supera el umbral mínimo.
4. Stake sugerido vía Kelly fraccional (quarter Kelly) con tope duro.

Claude entra después como capa de narrativa — no como decisor.
"""
from __future__ import annotations

from typing import Literal, TypedDict


Outcome = Literal["H", "D", "A"]

# Parámetros conservadores de bankroll management
MIN_EDGE_PP = 3.0          # edge mínimo en puntos porcentuales para recomendar pick
MIN_EV_PCT = 5.0           # EV mínimo en % para recomendar pick
KELLY_FRACTION = 0.25      # quarter Kelly — estándar profesional
MAX_STAKE_PCT = 5.0        # tope duro: nunca más del 5% del bankroll


class ProbTriplet(TypedDict):
    home: float
    draw: float
    away: float


class Pick(TypedDict):
    prediction: Outcome
    prediction_label: str
    confidence_pct: float
    market_implied_pct: float
    edge_pp: float
    ev_pct: float
    bookmaker_odds: float
    suggested_stake_pct: float
    kelly_raw_pct: float
    divergence_flag: bool
    recommended: bool
    reasoning: str
    all_outcomes: list[dict]


def _kelly_fraction(p: float, decimal_odds: float) -> float:
    """Kelly clásico: f* = (b*p - q) / b, con b = odds - 1."""
    b = decimal_odds - 1
    if b <= 0:
        return 0.0
    q = 1 - p
    f_star = (b * p - q) / b
    return max(0.0, f_star)


def _label(outcome: Outcome, home: str, away: str) -> str:
    return {
        "H": f"{home} gana",
        "D": "Empate",
        "A": f"{away} gana",
    }[outcome]


def generate_pick(
    home_team: str,
    away_team: str,
    ml_probs: ProbTriplet,
    bookmaker_probs: ProbTriplet,
    bookmaker_odds: dict[Outcome, float],
    home_form: dict | None = None,
    away_form: dict | None = None,
) -> Pick:
    """Produce un pick determinista a partir de las 2 capas de probabilidad."""
    outcomes: list[Outcome] = ["H", "D", "A"]
    prob_keys = {"H": "home", "D": "draw", "A": "away"}

    evaluated = []
    for o in outcomes:
        k = prob_keys[o]
        p_ours = ml_probs[k]
        p_market = bookmaker_probs[k]
        odds = bookmaker_odds[o]
        edge_pp = (p_ours - p_market) * 100
        ev_pct = (p_ours * odds - 1) * 100
        kelly_raw = _kelly_fraction(p_ours, odds) * 100

        evaluated.append({
            "outcome": o,
            "label": _label(o, home_team, away_team),
            "our_prob_pct": round(float(p_ours) * 100, 2),
            "market_prob_pct": round(float(p_market) * 100, 2),
            "odds": float(odds),
            "edge_pp": round(float(edge_pp), 2),
            "ev_pct": round(float(ev_pct), 2),
            "kelly_raw_pct": round(float(kelly_raw), 2),
        })

    # Mejor pick = mayor EV con edge > mínimo
    ranked = sorted(evaluated, key=lambda x: x["ev_pct"], reverse=True)
    best = ranked[0]

    recommended = (
        best["edge_pp"] >= MIN_EDGE_PP
        and best["ev_pct"] >= MIN_EV_PCT
    )

    stake = 0.0
    if recommended:
        stake = min(best["kelly_raw_pct"] * KELLY_FRACTION, MAX_STAKE_PCT)

    reasoning = _build_reasoning(
        best, ranked, home_team, away_team, home_form, away_form, recommended
    )

    return {
        "prediction": best["outcome"],
        "prediction_label": best["label"],
        "confidence_pct": float(best["our_prob_pct"]),
        "market_implied_pct": float(best["market_prob_pct"]),
        "edge_pp": float(best["edge_pp"]),
        "ev_pct": float(best["ev_pct"]),
        "bookmaker_odds": float(best["odds"]),
        "suggested_stake_pct": round(float(stake), 2),
        "kelly_raw_pct": float(best["kelly_raw_pct"]),
        "divergence_flag": bool(abs(best["edge_pp"]) >= 5.0),
        "recommended": bool(recommended),
        "reasoning": reasoning,
        "all_outcomes": ranked,
    }


def _build_reasoning(
    best: dict,
    ranked: list[dict],
    home: str,
    away: str,
    home_form: dict | None,
    away_form: dict | None,
    recommended: bool,
) -> str:
    lines = []

    if recommended:
        lines.append(
            f"Pick: {best['label']} @ {best['odds']:.2f}. "
            f"Nuestra probabilidad ({best['our_prob_pct']:.1f}%) supera a la del "
            f"mercado ({best['market_prob_pct']:.1f}%) en {best['edge_pp']:+.1f} pp, "
            f"dando EV de {best['ev_pct']:+.1f}%."
        )
    else:
        lines.append(
            f"Sin edge suficiente. Mejor EV disponible: {best['label']} "
            f"({best['ev_pct']:+.1f}%), por debajo del umbral de {MIN_EV_PCT}%."
        )

    if home_form and away_form:
        lines.append(
            f"Forma reciente: {home} {home_form['Form']:.2f} pts/g "
            f"(GF {home_form['avg_GF']:.2f}, GA {home_form['avg_GA']:.2f}) "
            f"vs {away} {away_form['Form']:.2f} pts/g "
            f"(GF {away_form['avg_GF']:.2f}, GA {away_form['avg_GA']:.2f})."
        )

    # Contexto sobre las otras opciones
    losing = [o for o in ranked if o["outcome"] != best["outcome"]]
    if losing:
        worst_ev_strs = [f"{o['label']} {o['ev_pct']:+.1f}%" for o in losing]
        lines.append(f"Resto de EV: {', '.join(worst_ev_strs)}.")

    return " ".join(lines)
