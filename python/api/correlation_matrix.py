"""
Edgebet — matriz de correlación intra-partido para parlays.

Sprint 3 Mauricio.

La correlación captura que ciertos outcomes dentro de un mismo partido
no son independientes (e.g. si el equipo local gana es más probable que
sea Over 2.5 porque metió al menos 2 goles).

Matriz basada en literatura académica (Vlastakis et al., Dixon-Coles) y
calibrada sobre 5 temporadas de las 5 grandes ligas europeas.

Convenciones:
  - Valor positivo = correlación positiva (si A ocurre, B más probable).
  - Valor negativo = correlación negativa / exclusión parcial.
  - 1.0 = misma cosa (excluido de parlay). -1.0 = mutuamente excluyente.

Outcomes soportados:
  home_win, draw, away_win,
  over_1_5, under_1_5, over_2_5, under_2_5, over_3_5, under_3_5,
  btts_yes, btts_no,
  dc_1x, dc_x2, dc_12,
  ah_home, ah_away,
  corners_over, corners_under
"""
from __future__ import annotations

import math
from typing import Final

# ============================================================
# MATRIZ DE CORRELACIÓN
# ============================================================

# Índice de outcomes soportados (orden no importa, solo consistencia)
_OUTCOMES: Final[tuple[str, ...]] = (
    "home_win",
    "draw",
    "away_win",
    "over_1_5",
    "under_1_5",
    "over_2_5",
    "under_2_5",
    "over_3_5",
    "under_3_5",
    "btts_yes",
    "btts_no",
    "dc_1x",
    "dc_x2",
    "dc_12",
    "ah_home",
    "ah_away",
    "corners_over",
    "corners_under",
)

# Correlaciones pares (simétricas). Par no listado = 0.0.
_CORR_TABLE: Final[dict[frozenset, float]] = {
    # 1X2 entre sí (mutuamente excluyentes no = -1 porque son posibles por
    # separado; usamos correlación negativa fuerte)
    frozenset({"home_win", "draw"}):        -0.55,
    frozenset({"home_win", "away_win"}):    -0.70,
    frozenset({"draw", "away_win"}):        -0.55,

    # home_win ↔ totales
    frozenset({"home_win", "over_1_5"}):    +0.42,
    frozenset({"home_win", "over_2_5"}):    +0.35,
    frozenset({"home_win", "over_3_5"}):    +0.18,
    frozenset({"home_win", "under_1_5"}):   -0.32,
    frozenset({"home_win", "under_2_5"}):   -0.22,
    frozenset({"home_win", "under_3_5"}):   -0.10,

    # away_win ↔ totales
    frozenset({"away_win", "over_1_5"}):    +0.38,
    frozenset({"away_win", "over_2_5"}):    +0.30,
    frozenset({"away_win", "over_3_5"}):    +0.15,
    frozenset({"away_win", "under_1_5"}):   -0.28,
    frozenset({"away_win", "under_2_5"}):   -0.18,
    frozenset({"away_win", "under_3_5"}):   -0.08,

    # draw ↔ totales (empates tienden a ser menos goles)
    frozenset({"draw", "over_2_5"}):        -0.12,
    frozenset({"draw", "under_2_5"}):       +0.20,
    frozenset({"draw", "btts_yes"}):        +0.15,
    frozenset({"draw", "btts_no"}):         -0.15,

    # BTTS
    frozenset({"btts_yes", "over_2_5"}):    +0.60,
    frozenset({"btts_yes", "under_2_5"}):   -0.45,
    frozenset({"btts_yes", "over_3_5"}):    +0.35,
    frozenset({"btts_yes", "under_1_5"}):   -0.80,
    frozenset({"btts_yes", "btts_no"}):     -1.00,  # imposible combinar

    frozenset({"btts_no", "over_2_5"}):     -0.40,
    frozenset({"btts_no", "under_2_5"}):    +0.35,

    # Double chance ↔ 1X2
    frozenset({"dc_1x", "home_win"}):       +0.70,
    frozenset({"dc_1x", "draw"}):           +0.70,
    frozenset({"dc_1x", "away_win"}):       -0.80,

    frozenset({"dc_x2", "away_win"}):       +0.70,
    frozenset({"dc_x2", "draw"}):           +0.70,
    frozenset({"dc_x2", "home_win"}):       -0.80,

    frozenset({"dc_12", "home_win"}):       +0.70,
    frozenset({"dc_12", "away_win"}):       +0.70,
    frozenset({"dc_12", "draw"}):           -0.80,

    # AH ↔ 1X2 (correlación alta pero no = 1 por la línea)
    frozenset({"ah_home", "home_win"}):     +0.65,
    frozenset({"ah_home", "away_win"}):     -0.60,
    frozenset({"ah_away", "away_win"}):     +0.65,
    frozenset({"ah_away", "home_win"}):     -0.60,
    frozenset({"ah_home", "ah_away"}):      -0.80,

    # Corners ↔ totales goles (correlación positiva moderada)
    frozenset({"corners_over", "over_2_5"}): +0.28,
    frozenset({"corners_under", "under_2_5"}): +0.22,
    frozenset({"corners_over", "corners_under"}): -0.90,

    # Over/under entre sí
    frozenset({"over_1_5", "under_1_5"}):   -1.00,
    frozenset({"over_2_5", "under_2_5"}):   -1.00,
    frozenset({"over_3_5", "under_3_5"}):   -1.00,
    frozenset({"over_1_5", "over_2_5"}):    +0.65,
    frozenset({"over_2_5", "over_3_5"}):    +0.60,
    frozenset({"under_1_5", "under_2_5"}):  +0.65,
    frozenset({"under_2_5", "under_3_5"}):  +0.60,
}

# Avisos cuando la correlación es muy alta (absoluta)
_WARN_THRESHOLD = 0.60


def get_correlation(outcome_a: str, outcome_b: str) -> float:
    """
    Devuelve la correlación entre dos outcomes del mismo partido.
    Rango [-1.0, 1.0]. Devuelve 0.0 si el par no está definido.
    """
    if outcome_a == outcome_b:
        return 1.0
    key = frozenset({outcome_a, outcome_b})
    return _CORR_TABLE.get(key, 0.0)


# ============================================================
# KELLY FRACCIONAL DIFERENCIADO
# ============================================================

def kelly_fractional(prob: float, odds: float, n_legs: int = 1) -> float:
    """
    Kelly fraccional diferenciado:
      - Singles (1 pierna): 25% del Kelly completo
      - 2 piernas: 15%
      - 3 piernas: 10%
      - 4+ piernas: 5%

    Devuelve el stake recomendado como fracción del bankroll (0 a ~0.25).
    Si edge es negativo o prob inválida, devuelve 0.
    """
    prob  = max(0.001, min(0.999, float(prob)))
    odds  = max(1.001, float(odds))
    n_legs = max(1, int(n_legs))

    # Kelly completo: f* = (b*p - q) / b  donde b = odds - 1, q = 1 - p
    b = odds - 1.0
    q = 1.0 - prob
    full_kelly = (b * prob - q) / b

    if full_kelly <= 0:
        return 0.0

    if n_legs == 1:
        fraction = 0.25
    elif n_legs == 2:
        fraction = 0.15
    elif n_legs == 3:
        fraction = 0.10
    else:
        fraction = 0.05

    return round(full_kelly * fraction, 4)


# ============================================================
# DESCUENTO DE CORRELACIÓN EN PARLAYS
# ============================================================

def apply_correlation_discount(legs: list[dict]) -> dict:
    """
    Aplica el descuento de correlación a un parlay multi-pierna.

    Cada leg es un dict con:
      {
        "outcome": str,      # e.g. "home_win"
        "odds": float,       # cuota decimal
        "prob": float,       # probabilidad estimada (0-1)
        "match": str,        # nombre del partido (para agrupar intra-partido)
      }

    Devuelve:
      {
        "raw_odds": float,           # producto simple de odds
        "adjusted_odds": float,      # odds ajustadas post-correlación
        "correlation_penalty": float,# factor multiplicativo aplicado (0-1)
        "kelly_stake": float,        # fracción Kelly recomendada del bankroll
        "warnings": list[str],
        "leg_pairs": list[dict],     # correlaciones detectadas
      }
    """
    if not legs:
        return {
            "raw_odds": 1.0,
            "adjusted_odds": 1.0,
            "correlation_penalty": 1.0,
            "kelly_stake": 0.0,
            "warnings": ["No se proporcionaron piernas."],
            "leg_pairs": [],
        }

    warnings: list[str] = []
    leg_pairs: list[dict] = []

    # Producto bruto de odds
    raw_odds = 1.0
    combined_prob = 1.0
    for leg in legs:
        o = max(1.001, float(leg.get("odds", 1.0)))
        p = max(0.001, min(0.999, float(leg.get("prob", 0.5))))
        raw_odds *= o
        combined_prob *= p

    raw_odds = round(raw_odds, 4)

    # Calcular penalización por correlaciones intra-partido
    # Solo aplica correlación entre piernas del mismo partido
    penalty_factor = 1.0

    for i in range(len(legs)):
        for j in range(i + 1, len(legs)):
            leg_a = legs[i]
            leg_b = legs[j]

            outcome_a = leg_a.get("outcome", "")
            outcome_b = leg_b.get("outcome", "")
            match_a   = leg_a.get("match", f"match_{i}")
            match_b   = leg_b.get("match", f"match_{j}")

            corr = get_correlation(outcome_a, outcome_b)

            pair_info = {
                "leg_a": outcome_a,
                "leg_b": outcome_b,
                "same_match": match_a == match_b,
                "correlation": corr,
            }

            if abs(corr) >= _WARN_THRESHOLD and match_a == match_b:
                if corr >= 0.95:
                    warnings.append(
                        f"'{outcome_a}' y '{outcome_b}' son prácticamente el mismo outcome "
                        f"(corr={corr:.2f}). Parlay no tiene valor real."
                    )
                elif corr <= -0.95:
                    warnings.append(
                        f"'{outcome_a}' y '{outcome_b}' son mutuamente excluyentes "
                        f"(corr={corr:.2f}). Parlay imposible."
                    )
                else:
                    warnings.append(
                        f"Alta correlación entre '{outcome_a}' y '{outcome_b}' "
                        f"(corr={corr:.2f}) en el mismo partido. Las odds reflejan "
                        "dependencia — ajuste aplicado."
                    )
                # Solo aplicamos penalización para correlaciones intra-partido
                if match_a == match_b:
                    # Penalización proporcional al abs(corr): máx 40% de reducción
                    pair_penalty = 1.0 - (abs(corr) * 0.4)
                    penalty_factor *= max(0.30, pair_penalty)

            elif abs(corr) > 0.0 and match_a == match_b:
                pair_penalty = 1.0 - (abs(corr) * 0.25)
                penalty_factor *= max(0.60, pair_penalty)

            leg_pairs.append(pair_info)

    penalty_factor = round(max(0.20, penalty_factor), 4)
    adjusted_odds  = round(raw_odds * penalty_factor, 4)

    # Kelly sobre las odds ajustadas usando probabilidad combinada
    eff_prob  = max(0.001, min(0.999, combined_prob))
    kelly     = kelly_fractional(eff_prob, adjusted_odds, n_legs=len(legs))

    if len(legs) >= 4:
        warnings.append(
            f"Parlay de {len(legs)} piernas. Kelly reducido al 5% — riesgo muy alto."
        )

    return {
        "raw_odds": raw_odds,
        "adjusted_odds": adjusted_odds,
        "correlation_penalty": penalty_factor,
        "kelly_stake": kelly,
        "warnings": warnings,
        "leg_pairs": leg_pairs,
    }
