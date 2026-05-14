"""
Edgebet — mercados de Goles (Over/Under) y Doble Oportunidad vía Poisson.

Modelo:
  λ_home = avg_GF_home * (avg_GA_away / liga_avg_GA)  (ataque local × debilidad visitante)
  λ_away = avg_GF_away * (avg_GA_home / liga_avg_GA)
Ajuste de ventaja local: +0.30 a λ_home (calibrado a Premier League histórica ~1.55 vs ~1.20).

Generamos la matriz de score independiente:
  P(i,j) = poisson(i; λ_home) * poisson(j; λ_away)
y derivamos:
  - P(over_X.5)   = Σ P(i,j) sobre i+j > X
  - P(under_X.5)  = 1 - P(over_X.5)
  - P(1X)         = P(home win) + P(draw)
  - P(X2)         = P(draw) + P(away win)
  - P(12)         = P(home win) + P(away win)

Se asume independencia (Dixon-Coles tau = 0). En la práctica los picks de
mercado vienen del mismo modelo Poisson que usa el bookie, así que el edge
viene de la diferencia entre nuestro λ y el suyo, no del corregimiento de
correlación.
"""
from __future__ import annotations

import math
from typing import Literal, TypedDict

# Promedio de goles por equipo en las 5 grandes ligas (2024/25). Se usa
# como denominador en el cálculo de λ ajustado por debilidad defensiva.
LEAGUE_AVG_GOALS_PER_TEAM = 1.40

# Boost de ventaja local. Calibrado contra Premier League histórica donde
# el local marca ~0.30 goles más que el visitante a igualdad de fuerza.
HOME_ADVANTAGE_LAMBDA = 0.30

# Truncamos la matriz Poisson aquí — P(>10 goles por equipo) ≈ 0 incluso
# para λ=4. Usar 11 da error <1e-6 en marginales.
MAX_GOALS_PER_TEAM = 10


GoalLine = Literal[1.5, 2.5, 3.5]


MarketKey = Literal["OU", "DC", "BTTS", "TEAM_TOTALS", "SPREAD", "ML"]


class MarketOutcome(TypedDict):
    market: MarketKey
    outcome: str
    label: str
    our_prob_pct: float
    market_prob_pct: float | None
    odds: float | None
    edge_pp: float | None
    ev_pct: float | None


def _poisson_pmf(k: int, lam: float) -> float:
    """P(X=k) para Poisson(lam). Versión numéricamente estable."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _expected_goals(home_form: dict, away_form: dict) -> tuple[float, float]:
    """Estima λ_home y λ_away a partir de la forma reciente de cada equipo."""
    home_gf = max(0.1, float(home_form.get("avg_GF", 1.20)))
    home_ga = max(0.1, float(home_form.get("avg_GA", 1.20)))
    away_gf = max(0.1, float(away_form.get("avg_GF", 1.10)))
    away_ga = max(0.1, float(away_form.get("avg_GA", 1.30)))

    # Producto: ataque del equipo × ratio de la defensa rival vs media de liga.
    # Si la defensa rival es peor que la media (>1.0), λ sube.
    lam_home = home_gf * (away_ga / LEAGUE_AVG_GOALS_PER_TEAM) + HOME_ADVANTAGE_LAMBDA
    lam_away = away_gf * (home_ga / LEAGUE_AVG_GOALS_PER_TEAM)

    # Bound mínimo para evitar λ=0 que rompe el blend con probs de mercado
    return max(0.15, lam_home), max(0.15, lam_away)


def _score_matrix(lam_home: float, lam_away: float) -> list[list[float]]:
    """Matriz P(i,j) bajo independencia."""
    home_pmf = [_poisson_pmf(i, lam_home) for i in range(MAX_GOALS_PER_TEAM + 1)]
    away_pmf = [_poisson_pmf(j, lam_away) for j in range(MAX_GOALS_PER_TEAM + 1)]
    return [[home_pmf[i] * away_pmf[j] for j in range(MAX_GOALS_PER_TEAM + 1)] for i in range(MAX_GOALS_PER_TEAM + 1)]


def _outcome_probs(matrix: list[list[float]]) -> dict[str, float]:
    """Marginaliza la matriz en home/draw/away y over/under en 1.5, 2.5, 3.5."""
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over = {1.5: 0.0, 2.5: 0.0, 3.5: 0.0}

    for i in range(MAX_GOALS_PER_TEAM + 1):
        for j in range(MAX_GOALS_PER_TEAM + 1):
            p = matrix[i][j]
            total = i + j
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p
            for line in (1.5, 2.5, 3.5):
                if total > line:
                    over[line] += p

    # Normaliza mínimas pérdidas por truncamiento
    s = home_win + draw + away_win
    if s > 0:
        home_win, draw, away_win = home_win / s, draw / s, away_win / s

    return {
        "home": home_win,
        "draw": draw,
        "away": away_win,
        "over_1_5": over[1.5],
        "under_1_5": 1.0 - over[1.5],
        "over_2_5": over[2.5],
        "under_2_5": 1.0 - over[2.5],
        "over_3_5": over[3.5],
        "under_3_5": 1.0 - over[3.5],
    }


_OU_LABEL = {
    "over_1_5": "Más de 1.5 goles",
    "under_1_5": "Menos de 1.5 goles",
    "over_2_5": "Más de 2.5 goles",
    "under_2_5": "Menos de 2.5 goles",
    "over_3_5": "Más de 3.5 goles",
    "under_3_5": "Menos de 3.5 goles",
}


def _evaluate_outcome(
    outcome: str,
    market: MarketKey,
    label: str,
    our_prob: float,
    market_prob: float | None,
    odds: float | None,
) -> MarketOutcome:
    edge_pp: float | None = None
    ev_pct: float | None = None
    if market_prob is not None and odds is not None:
        edge_pp = round((our_prob - market_prob) * 100, 2)
        ev_pct = round((our_prob * odds - 1.0) * 100, 2)
    return {
        "market": market,
        "outcome": outcome,
        "label": label,
        "our_prob_pct": round(our_prob * 100, 2),
        "market_prob_pct": round(market_prob * 100, 2) if market_prob is not None else None,
        "odds": float(odds) if odds is not None else None,
        "edge_pp": edge_pp,
        "ev_pct": ev_pct,
    }


def _team_total_probs(lam: float) -> dict[str, float]:
    """P(team scores >= N+0.5) para varios totals individuales por equipo."""
    cum = [_poisson_pmf(k, lam) for k in range(MAX_GOALS_PER_TEAM + 1)]
    over_0_5 = 1.0 - cum[0]
    over_1_5 = 1.0 - cum[0] - cum[1]
    over_2_5 = 1.0 - cum[0] - cum[1] - cum[2]
    return {
        "over_0_5": max(0.0, over_0_5),
        "under_0_5": min(1.0, cum[0]),
        "over_1_5": max(0.0, over_1_5),
        "under_1_5": min(1.0, cum[0] + cum[1]),
        "over_2_5": max(0.0, over_2_5),
        "under_2_5": min(1.0, cum[0] + cum[1] + cum[2]),
    }


def _btts_probs(lam_home: float, lam_away: float) -> dict[str, float]:
    """P(BTTS=Yes) = P(home>=1) * P(away>=1) bajo independencia Poisson."""
    p_h_scores = 1.0 - math.exp(-lam_home)
    p_a_scores = 1.0 - math.exp(-lam_away)
    btts_yes = p_h_scores * p_a_scores
    btts_yes = max(0.02, min(0.98, btts_yes))
    return {"yes": btts_yes, "no": 1.0 - btts_yes}


SPREAD_LINES = (-2.5, -1.5, -0.5, 0.5, 1.5, 2.5)


def _spread_probs(matrix: list[list[float]]) -> dict[str, dict[str, float]]:
    """
    Calcula P(home cubre handicap line) y P(away cubre opuesto) para varias
    líneas de Asian Handicap. Para handicap -1.5 home necesita ganar por 2+,
    etc. Convención: el `line_key` se firma desde la perspectiva del home
    ("-1.5" = local con -1.5, "+1.5" = local con +1.5).
    """
    result: dict[str, dict[str, float]] = {}
    for line in SPREAD_LINES:
        # P(home cubre handicap `line`): home_goals + line > away_goals
        p_home = 0.0
        for i in range(MAX_GOALS_PER_TEAM + 1):
            for j in range(MAX_GOALS_PER_TEAM + 1):
                if (i + line) > j:
                    p_home += matrix[i][j]
        p_away = 1.0 - p_home  # complemento (ignoramos push exacto, line .5 evita ties)
        key = f"{line:+.1f}"
        result[key] = {"home": p_home, "away": p_away}
    return result


def build_market_outcomes(
    home_form: dict,
    away_form: dict,
    home_team: str,
    away_team: str,
    one_x_two_probs: dict | None = None,
) -> dict:
    """
    Genera probabilidades para mercados secundarios derivados de Poisson:
      - OU goles totales (1.5, 2.5, 3.5)
      - Doble oportunidad (1X, X2, 12) — derivada del blend 1X2 si está disponible
      - BTTS (Yes/No)
      - Team totals (home over 0.5/1.5/2.5, away over 0.5/1.5/2.5)

    Todas las probs vienen del mismo modelo Poisson para que sean coherentes
    entre sí (P(BTTS) y P(over 1.5) por ejemplo no se contradigan).
    """
    lam_home, lam_away = _expected_goals(home_form, away_form)
    matrix = _score_matrix(lam_home, lam_away)
    probs = _outcome_probs(matrix)

    if one_x_two_probs:
        h = float(one_x_two_probs.get("home", probs["home"]))
        d = float(one_x_two_probs.get("draw", probs["draw"]))
        a = float(one_x_two_probs.get("away", probs["away"]))
    else:
        h, d, a = probs["home"], probs["draw"], probs["away"]

    dc = {
        "1X": min(1.0, h + d),
        "X2": min(1.0, d + a),
        "12": min(1.0, h + a),
    }

    ou_outcomes = [
        _evaluate_outcome(key, "OU", _OU_LABEL[key], probs[key], None, None)
        for key in ("over_1_5", "under_1_5", "over_2_5", "under_2_5", "over_3_5", "under_3_5")
    ]
    dc_outcomes = [
        _evaluate_outcome("1X", "DC", f"{home_team} o Empate", dc["1X"], None, None),
        _evaluate_outcome("X2", "DC", f"Empate o {away_team}", dc["X2"], None, None),
        _evaluate_outcome("12", "DC", f"{home_team} o {away_team}", dc["12"], None, None),
    ]

    btts = _btts_probs(lam_home, lam_away)
    btts_outcomes = [
        _evaluate_outcome("yes", "BTTS", "Ambos anotan: Sí", btts["yes"], None, None),
        _evaluate_outcome("no", "BTTS", "Ambos anotan: No", btts["no"], None, None),
    ]

    home_team_totals = _team_total_probs(lam_home)
    away_team_totals = _team_total_probs(lam_away)
    team_totals_outcomes = [
        _evaluate_outcome(
            f"home_{k}", "TEAM_TOTALS",
            f"{home_team} {_team_total_label(k)}",
            home_team_totals[k], None, None,
        )
        for k in ("over_0_5", "over_1_5", "over_2_5", "under_0_5", "under_1_5", "under_2_5")
    ] + [
        _evaluate_outcome(
            f"away_{k}", "TEAM_TOTALS",
            f"{away_team} {_team_total_label(k)}",
            away_team_totals[k], None, None,
        )
        for k in ("over_0_5", "over_1_5", "over_2_5", "under_0_5", "under_1_5", "under_2_5")
    ]

    spread_probs = _spread_probs(matrix)
    spread_outcomes: list[MarketOutcome] = []
    for line_key, sides in spread_probs.items():
        spread_outcomes.append(_evaluate_outcome(
            f"home_{line_key}", "SPREAD",
            f"{home_team} {line_key}",
            sides["home"], None, None,
        ))
        spread_outcomes.append(_evaluate_outcome(
            f"away_{line_key}", "SPREAD",
            f"{away_team} {_invert_line(line_key)}",
            sides["away"], None, None,
        ))

    return {
        "lambda_home": round(lam_home, 3),
        "lambda_away": round(lam_away, 3),
        "expected_total_goals": round(lam_home + lam_away, 2),
        "ou_outcomes": ou_outcomes,
        "dc_outcomes": dc_outcomes,
        "btts_outcomes": btts_outcomes,
        "team_totals_outcomes": team_totals_outcomes,
        "spread_outcomes": spread_outcomes,
        "raw_probs": {k: round(v, 4) for k, v in probs.items()},
    }


def _invert_line(line_key: str) -> str:
    """'-1.5' → '+1.5', '+0.5' → '-0.5'"""
    sign = "+" if line_key.startswith("-") else "-"
    return f"{sign}{line_key[1:]}"


def _team_total_label(key: str) -> str:
    parts = key.split("_")
    side = parts[0]  # over / under
    line = f"{parts[1]}.{parts[2]}"
    side_word = "más de" if side == "over" else "menos de"
    return f"{side_word} {line} goles"


def best_secondary_market_pick(
    market_data: dict,
    min_confidence_pct: float = 65.0,
) -> dict | None:
    """
    Elige el outcome OU/DC más fuerte si supera el umbral.

    Sin línea de mercado verificada para OU/DC no podemos calcular edge ni
    EV — devolvemos solo el outcome con mayor confianza pura para que el
    pick sea informativo (no recomendación de apuesta).
    """
    candidates: list[dict] = list(market_data["ou_outcomes"]) + list(market_data["dc_outcomes"])
    if not candidates:
        return None
    candidates.sort(key=lambda o: o["our_prob_pct"], reverse=True)
    top = candidates[0]
    if top["our_prob_pct"] < min_confidence_pct:
        return None
    return top
