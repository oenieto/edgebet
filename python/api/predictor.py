"""
Edgebet — predictor en runtime.

Carga el ensemble entrenado (si existe) y genera probabilidades ML
para un enfrentamiento dado, reutilizando el histórico real ya cargado.
Si no hay modelo entrenado, cae a probabilidades derivadas de ELO.
"""
from __future__ import annotations

import math
import pickle
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

FEATURE_COLUMNS = [
    "home_avg_GF", "home_avg_GA", "home_avg_Shots", "home_avg_SoT",
    "home_avg_Corners", "home_Form",
    "away_avg_GF", "away_avg_GA", "away_avg_Shots", "away_avg_SoT",
    "away_avg_Corners", "away_Form",
    "diff_avg_GF", "diff_avg_GA", "diff_Form",
    "elo_home", "elo_away", "elo_diff", "elo_expected_home",
    "home_xG_proxy", "away_xG_proxy", "diff_xG_proxy",
    "home_rest_days", "away_rest_days", "rest_advantage",
    "norm_prob_H", "norm_prob_D", "norm_prob_A",
]


@dataclass
class PredictorArtifacts:
    ensemble: object
    scaler: object
    feature_columns: list[str]
    trained_at: str


@lru_cache(maxsize=1)
def _load_latest_artifacts() -> Optional[PredictorArtifacts]:
    """Carga el ensemble más reciente del disco. None si no hay artefactos."""
    if not MODELS_DIR.exists():
        return None

    ensembles = sorted(MODELS_DIR.glob("ensemble_*.pkl"))
    scalers = sorted(MODELS_DIR.glob("scaler_*.pkl"))
    if not ensembles or not scalers:
        return None

    try:
        with open(ensembles[-1], "rb") as f:
            ensemble = pickle.load(f)
        with open(scalers[-1], "rb") as f:
            scaler = pickle.load(f)
    except Exception as exc:
        print(f"[predictor] no pude cargar artefactos: {exc}")
        return None

    feat_path = MODELS_DIR / "feature_columns.txt"
    feature_columns = FEATURE_COLUMNS
    if feat_path.exists():
        feature_columns = [
            line.strip() for line in feat_path.read_text().splitlines() if line.strip()
        ]

    ts = ensembles[-1].stem.replace("ensemble_", "")
    return PredictorArtifacts(
        ensemble=ensemble,
        scaler=scaler,
        feature_columns=feature_columns,
        trained_at=ts,
    )


def artifacts_available() -> bool:
    return _load_latest_artifacts() is not None


def artifacts_info() -> dict:
    art = _load_latest_artifacts()
    if not art:
        return {"available": False}
    return {
        "available": True,
        "trained_at": art.trained_at,
        "n_features": len(art.feature_columns),
    }


def _compute_xg_proxy(sot: float, shots: float) -> float:
    sot = max(sot or 0.0, 0.0)
    shots = max(shots or 0.0, 0.0)
    return sot * 0.30 + max(shots - sot, 0.0) * 0.03


def _compute_rest_days(matches: list[dict], team: str, as_of: datetime) -> int:
    for m in reversed(matches):
        if m["HomeTeam"] == team or m["AwayTeam"] == team:
            last_date = m.get("DateObj")
            if isinstance(last_date, datetime):
                delta = (as_of - last_date).days
                if delta <= 0:
                    return 7
                return min(delta, 30)
    return 14


def _elo_to_3way(p_home_raw: float, base_draw: float = 0.26) -> dict:
    return {
        "home": float(p_home_raw) * (1 - base_draw),
        "draw": base_draw,
        "away": (1 - float(p_home_raw)) * (1 - base_draw),
    }


def baseline_elo_probs(
    home_rating: float, away_rating: float, home_advantage: int = 65
) -> dict:
    p_home = 1.0 / (1.0 + 10 ** ((away_rating - (home_rating + home_advantage)) / 400.0))
    return _elo_to_3way(p_home)


def build_feature_row(
    home_team: str,
    away_team: str,
    matches: list[dict],
    elo_ratings: dict[str, float],
    home_form: dict,
    away_form: dict,
    bookmaker_probs: dict,
    as_of: Optional[datetime] = None,
) -> dict:
    """Construye una fila de features exactamente con las columnas del ensemble."""
    as_of = as_of or datetime.utcnow()
    home_rating = float(elo_ratings.get(home_team, 1500.0))
    away_rating = float(elo_ratings.get(away_team, 1500.0))
    elo_diff = home_rating - away_rating
    elo_expected_home = 1.0 / (1.0 + 10 ** ((away_rating - (home_rating + 65)) / 400.0))

    # Defaults de liga para stats que openfootball no expone (shots/SoT/corners).
    # Si llegan 0.0 asumimos missing data — un equipo no tiene 0 remates reales en 5 partidos.
    def _or_league_avg(val, default):
        v = float(val or 0.0)
        return v if v > 0 else default

    home_shots = _or_league_avg(home_form.get("avg_Shots"), 11.5)
    home_sot = _or_league_avg(home_form.get("avg_SoT"), 4.2)
    home_corners = _or_league_avg(home_form.get("avg_Corners"), 5.0)
    away_shots = _or_league_avg(away_form.get("avg_Shots"), 10.8)
    away_sot = _or_league_avg(away_form.get("avg_SoT"), 3.8)
    away_corners = _or_league_avg(away_form.get("avg_Corners"), 4.5)

    home_xg = _compute_xg_proxy(home_sot, home_shots)
    away_xg = _compute_xg_proxy(away_sot, away_shots)

    home_rest = _compute_rest_days(matches, home_team, as_of)
    away_rest = _compute_rest_days(matches, away_team, as_of)

    home_gf = float(home_form.get("avg_GF", 1.2))
    home_ga = float(home_form.get("avg_GA", 1.2))
    away_gf = float(away_form.get("avg_GF", 1.1))
    away_ga = float(away_form.get("avg_GA", 1.3))
    home_form_val = float(home_form.get("Form", 1.3))
    away_form_val = float(away_form.get("Form", 1.2))

    return {
        "home_avg_GF": home_gf,
        "home_avg_GA": home_ga,
        "home_avg_Shots": home_shots,
        "home_avg_SoT": home_sot,
        "home_avg_Corners": home_corners,
        "home_Form": home_form_val,
        "away_avg_GF": away_gf,
        "away_avg_GA": away_ga,
        "away_avg_Shots": away_shots,
        "away_avg_SoT": away_sot,
        "away_avg_Corners": away_corners,
        "away_Form": away_form_val,
        "diff_avg_GF": home_gf - away_gf,
        "diff_avg_GA": home_ga - away_ga,
        "diff_Form": home_form_val - away_form_val,
        "elo_home": home_rating,
        "elo_away": away_rating,
        "elo_diff": elo_diff,
        "elo_expected_home": elo_expected_home,
        "home_xG_proxy": home_xg,
        "away_xG_proxy": away_xg,
        "diff_xG_proxy": home_xg - away_xg,
        "home_rest_days": float(home_rest),
        "away_rest_days": float(away_rest),
        "rest_advantage": float(home_rest - away_rest),
        "norm_prob_H": float(bookmaker_probs.get("home", 0.45)),
        "norm_prob_D": float(bookmaker_probs.get("draw", 0.27)),
        "norm_prob_A": float(bookmaker_probs.get("away", 0.28)),
    }


def predict_ml_probs(
    home_team: str,
    away_team: str,
    matches: list[dict],
    elo_ratings: dict[str, float],
    home_form: dict,
    away_form: dict,
    bookmaker_probs: dict,
    as_of: Optional[datetime] = None,
) -> tuple[dict, str]:
    """
    Devuelve (probs_3way, source_tag).
    source_tag ∈ {"ensemble", "elo_fallback"}.
    """
    art = _load_latest_artifacts()
    if art is None:
        return (
            baseline_elo_probs(
                float(elo_ratings.get(home_team, 1500.0)),
                float(elo_ratings.get(away_team, 1500.0)),
            ),
            "elo_fallback",
        )

    try:
        import pandas as pd

        row = build_feature_row(
            home_team=home_team,
            away_team=away_team,
            matches=matches,
            elo_ratings=elo_ratings,
            home_form=home_form,
            away_form=away_form,
            bookmaker_probs=bookmaker_probs,
            as_of=as_of,
        )
        x_df = pd.DataFrame([[row.get(c, 0.0) for c in art.feature_columns]], columns=art.feature_columns)
        x_scaled = art.scaler.transform(x_df)
        proba = art.ensemble.predict_proba(x_scaled)[0]
        # Clase mapping del entrenamiento: 0=Away, 1=Draw, 2=Home
        return (
            {
                "home": float(proba[2]),
                "draw": float(proba[1]),
                "away": float(proba[0]),
            },
            "ensemble",
        )
    except Exception as exc:
        print(f"[predictor] fallo en inferencia, uso fallback ELO: {exc}")
        return (
            baseline_elo_probs(
                float(elo_ratings.get(home_team, 1500.0)),
                float(elo_ratings.get(away_team, 1500.0)),
            ),
            "elo_fallback",
        )


def triple_layer_blend(
    ml_probs: dict,
    bookmaker_probs: dict,
    polymarket_probs: Optional[dict] = None,
    weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
) -> dict:
    """
    Blend final:
      0.40 * ML + 0.35 * Polymarket + 0.25 * Bet365 (si hay Polymarket)
      0.60 * ML + 0.40 * Bet365 (si no hay Polymarket)
    """
    w_ml, w_poly, w_bk = weights
    if polymarket_probs is None:
        # Redistribuir el peso de Poly entre ML y BK (proporcional)
        total = w_ml + w_bk
        w_ml_n = w_ml / total
        w_bk_n = w_bk / total
        return {
            k: max(0.0, min(1.0, w_ml_n * ml_probs.get(k, 0) + w_bk_n * bookmaker_probs.get(k, 0)))
            for k in ("home", "draw", "away")
        }

    blended = {
        k: (
            w_ml * ml_probs.get(k, 0)
            + w_poly * polymarket_probs.get(k, 0)
            + w_bk * bookmaker_probs.get(k, 0)
        )
        for k in ("home", "draw", "away")
    }
    total = sum(blended.values()) or 1.0
    return {k: v / total for k, v in blended.items()}
