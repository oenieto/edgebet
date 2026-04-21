"""
Edgebet — generador de parlays (combinadas) a partir del pool diario de picks.

Lógica:
  1. Cada pick del día ya trae `allOutcomes` con (H/D/A × our_prob, odds, edge, EV).
  2. Filtramos outcomes cuya cuota cae en la banda del tier y cuyo edge > mínimo.
  3. Diversificamos: máx 1 leg por partido, máx 1 leg por liga (proxy de correlación).
  4. Enumeramos combinaciones de 3 legs. Nos quedamos con la de mayor EV combinado
     cuya cuota producto caiga dentro de la banda objetivo del tier.
  5. Kelly fraccional sobre el EV combinado (más conservador que singles: stake/3).

Tiers:
  safe    — 3 legs de 1.08–1.30 → ~1.33 combined (favoritos sólidos)
  medium  — 3 legs de 1.15–1.45 → ~1.73 combined (mix ponderado)
  risky   — 3 legs de 1.40–1.90 → ~4.10 combined (underdogs con valor)
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Literal

TierName = Literal["safe", "medium", "risky"]


@dataclass(frozen=True)
class ParlayTier:
    name: TierName
    min_leg_odds: float
    max_leg_odds: float
    n_legs: int
    target_combined: float
    tolerance: float  # factor multiplicativo: combinada válida en [target/(1+t), target*(1+t)]
    min_leg_edge_pp: float  # edge mínimo por leg (en pp)


TIERS: dict[TierName, ParlayTier] = {
    "safe": ParlayTier(
        name="safe",
        min_leg_odds=1.08,
        max_leg_odds=1.30,
        n_legs=3,
        target_combined=1.50,  # 3 legs a ~1.15 prom. — realista en mercados de favoritos
        tolerance=0.55,
        min_leg_edge_pp=1.0,
    ),
    "medium": ParlayTier(
        name="medium",
        min_leg_odds=1.18,
        max_leg_odds=1.55,
        n_legs=3,
        target_combined=2.20,  # 3 legs a ~1.30 prom.
        tolerance=0.50,
        min_leg_edge_pp=1.5,
    ),
    "risky": ParlayTier(
        name="risky",
        min_leg_odds=1.40,
        max_leg_odds=2.20,
        n_legs=3,
        target_combined=4.50,  # 3 legs a ~1.65 prom.
        tolerance=0.60,
        min_leg_edge_pp=1.5,
    ),
}

PREDICTION_MAP = {"H": "home", "D": "draw", "A": "away"}
MAX_PARLAY_STAKE_PCT = 1.5   # tope duro sobre bankroll para parlays (más conservador que singles)
KELLY_FRACTION = 0.10        # Kelly muy fraccional en combinadas


def _candidate_legs(picks: list[dict], tier: ParlayTier) -> list[dict]:
    """Aplana picks → lista de (match, outcome) válidos para el tier.

    Solo considera picks con línea de mercado real — los outcomes construidos
    sobre odds sintéticas fabrican edges artificiales que romperían la combinada.
    """
    candidates = []
    for p in picks:
        if not p.get("marketVerified"):
            continue
        outcomes = p.get("allOutcomes") or []
        for o in outcomes:
            odds = float(o.get("odds", 0))
            edge = float(o.get("edge_pp", 0))
            if not (tier.min_leg_odds <= odds <= tier.max_leg_odds):
                continue
            if edge < tier.min_leg_edge_pp:
                continue
            candidates.append({
                "match_id": p.get("id"),
                "match": p.get("match"),
                "league": p.get("league"),
                "leagueSlug": p.get("leagueSlug"),
                "homeTeam": p.get("homeTeam"),
                "awayTeam": p.get("awayTeam"),
                "kickoff": p.get("kickoff"),
                "outcome": o["outcome"],
                "prediction": PREDICTION_MAP.get(o["outcome"], o["outcome"]),
                "label": o["label"],
                "odds": odds,
                "our_prob_pct": float(o["our_prob_pct"]),
                "market_prob_pct": float(o["market_prob_pct"]),
                "edge_pp": edge,
                "ev_pct": float(o.get("ev_pct", 0)),
            })
    return candidates


def _diversified(legs: list[dict]) -> bool:
    """Reduce correlación entre patas sin bloquear CL-only pools.

    Reglas:
      - Ningún match repetido.
      - Ningún equipo aparece en dos legs (evita correlación por alineación/lesiones).
      - Máx 2 legs por liga (permite combinar varios matches CL o misma liga top).
    """
    if len({l["match_id"] for l in legs}) != len(legs):
        return False

    teams: list[str] = []
    for l in legs:
        teams.append(l["homeTeam"])
        teams.append(l["awayTeam"])
    if len(set(teams)) != len(teams):
        return False

    from collections import Counter
    league_counts = Counter(l["leagueSlug"] for l in legs)
    if any(c > 2 for c in league_counts.values()):
        return False
    return True


def _combined_metrics(legs: list[dict]) -> dict:
    combined_odds = 1.0
    joint_prob_ours = 1.0
    joint_prob_market = 1.0
    for l in legs:
        combined_odds *= l["odds"]
        joint_prob_ours *= l["our_prob_pct"] / 100.0
        joint_prob_market *= l["market_prob_pct"] / 100.0
    ev_pct = (joint_prob_ours * combined_odds - 1.0) * 100.0
    edge_pp = (joint_prob_ours - joint_prob_market) * 100.0
    return {
        "combined_odds": round(combined_odds, 3),
        "joint_prob_pct": round(joint_prob_ours * 100, 2),
        "market_joint_prob_pct": round(joint_prob_market * 100, 2),
        "ev_pct": round(ev_pct, 2),
        "edge_pp": round(edge_pp, 2),
    }


def _kelly_stake(joint_prob: float, combined_odds: float) -> float:
    b = combined_odds - 1.0
    if b <= 0 or joint_prob <= 0:
        return 0.0
    q = 1.0 - joint_prob
    f_star = (b * joint_prob - q) / b
    if f_star <= 0:
        return 0.0
    return round(min(f_star * KELLY_FRACTION * 100, MAX_PARLAY_STAKE_PCT), 2)


def build_parlay(picks: list[dict], tier_name: TierName) -> dict | None:
    """Devuelve el mejor parlay del tier, o None si no alcanza."""
    tier = TIERS[tier_name]
    candidates = _candidate_legs(picks, tier)
    if len(candidates) < tier.n_legs:
        return None

    # Orden descendente por EV individual para acelerar la búsqueda
    candidates.sort(key=lambda c: c["ev_pct"], reverse=True)
    # Limitar el espacio combinatorio: top 12 candidatos por tier
    candidates = candidates[:12]

    lo = tier.target_combined / (1 + tier.tolerance)
    hi = tier.target_combined * (1 + tier.tolerance)

    best: tuple[float, list[dict], dict] | None = None
    for combo in combinations(candidates, tier.n_legs):
        legs = list(combo)
        if not _diversified(legs):
            continue
        metrics = _combined_metrics(legs)
        if not (lo <= metrics["combined_odds"] <= hi):
            continue
        if metrics["ev_pct"] <= 0:
            continue
        score = metrics["ev_pct"]
        if best is None or score > best[0]:
            best = (score, legs, metrics)

    if best is None:
        return None

    _, legs, metrics = best
    joint_prob = metrics["joint_prob_pct"] / 100.0
    stake_pct = _kelly_stake(joint_prob, metrics["combined_odds"])

    return {
        "tier": tier.name,
        "n_legs": len(legs),
        "target_combined_odds": tier.target_combined,
        "legs": [
            {
                "match": l["match"],
                "league": l["league"],
                "leagueSlug": l["leagueSlug"],
                "kickoff": l["kickoff"],
                "prediction": l["prediction"],
                "label": l["label"],
                "odds": l["odds"],
                "our_prob_pct": l["our_prob_pct"],
                "market_prob_pct": l["market_prob_pct"],
                "edge_pp": l["edge_pp"],
                "ev_pct": l["ev_pct"],
            }
            for l in legs
        ],
        **metrics,
        "suggested_stake_pct": stake_pct,
        "reasoning": _build_reasoning(tier, legs, metrics, stake_pct),
    }


def build_all_tiers(picks: list[dict]) -> list[dict]:
    """Un parlay por tier. Omite tiers sin combo válida."""
    out = []
    for tier_name in ("safe", "medium", "risky"):
        parlay = build_parlay(picks, tier_name)  # type: ignore[arg-type]
        if parlay:
            out.append(parlay)
    return out


def _build_reasoning(tier: ParlayTier, legs: list[dict], metrics: dict, stake_pct: float) -> str:
    leg_strs = [f"{l['label']} @ {l['odds']:.2f}" for l in legs]
    narrative = (
        f"Parlay {tier.name} ({tier.n_legs} legs): "
        f"{' + '.join(leg_strs)}. "
        f"Cuota combinada {metrics['combined_odds']:.2f}. "
        f"Probabilidad conjunta {metrics['joint_prob_pct']:.1f}% vs mercado "
        f"{metrics['market_joint_prob_pct']:.1f}% → edge {metrics['edge_pp']:+.1f}pp, "
        f"EV {metrics['ev_pct']:+.1f}%. "
    )
    if stake_pct > 0:
        narrative += f"Stake sugerido: {stake_pct:.2f}% del bankroll (Kelly fraccional)."
    else:
        narrative += "Stake 0 — EV negativo tras compensar riesgo."
    return narrative
