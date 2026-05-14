"""
Edgebet — model calibration utilities.

Sprint 1 Antonio: Wraps any trained classifier with isotonic regression
calibration and provides reliability-diagram diagnostics.

Public API
----------
calibrate_ensemble(ensemble, X_val, y_val)
    -> CalibratedClassifierCV fitted on validation data

generate_reliability_diagram(y_true, y_proba, n_bins=10)
    -> dict with bins, fraction_of_positives, mean_predicted, brier_score, log_loss

evaluate_calibration(model, X_test, y_test)
    -> dict summary with brier_score, log_loss, accuracy
"""
from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


# ---------------------------------------------------------------------------
# Calibration wrapper
# ---------------------------------------------------------------------------

def calibrate_ensemble(ensemble, X_val, y_val):
    """
    Wraps `ensemble` with CalibratedClassifierCV(method='isotonic').

    Parameters
    ----------
    ensemble : fitted sklearn-compatible classifier
    X_val    : array-like, validation features (already scaled)
    y_val    : array-like, validation labels

    Returns
    -------
    Fitted CalibratedClassifierCV instance.

    Notes
    -----
    - cv='prefit' is used because the ensemble was already trained.
    - Isotonic regression is preferred over Platt scaling for ensembles
      because it is non-parametric and handles the multiclass case well.
    - Uses TimeSeriesSplit-compatible workflow: X_val must be a held-out
      set that strictly follows the training window in time.
    """
    try:
        from sklearn.calibration import CalibratedClassifierCV

        calibrated = CalibratedClassifierCV(
            estimator=ensemble,
            method="isotonic",
            cv="prefit",
        )
        calibrated.fit(X_val, y_val)
        return calibrated
    except Exception as exc:
        logger.error("[calibration] calibrate_ensemble failed: %s", exc)
        raise


def save_calibrated_model(calibrated_model, suffix: str = "calibrated") -> Path:
    """
    Persists the calibrated model to MODELS_DIR with a timestamp.

    Returns the Path where the file was saved.
    """
    import pickle

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = MODELS_DIR / f"ensemble_{ts}_{suffix}.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(calibrated_model, f)
    logger.info("[calibration] saved calibrated model → %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Reliability diagram
# ---------------------------------------------------------------------------

def generate_reliability_diagram(
    y_true,
    y_proba,
    n_bins: int = 10,
    *,
    pos_label: Optional[int] = None,
) -> dict:
    """
    Generates data for a reliability (calibration) diagram.

    For multiclass problems supply a 1-D `y_proba` for the positive class of
    interest (e.g. home-win column) and set `pos_label` accordingly.

    Parameters
    ----------
    y_true    : array-like of true labels
    y_proba   : array-like of predicted probabilities (1-D for binary / single class)
    n_bins    : number of equal-width bins in [0, 1]
    pos_label : label considered positive (binary case). If None the function
                expects y_true to already be 0/1.

    Returns
    -------
    dict with keys:
        bins                  : list[float]  — right edge of each bin
        fraction_of_positives : list[float]  — observed positive rate per bin
        mean_predicted        : list[float]  — mean predicted probability per bin
        counts                : list[int]    — number of samples per bin
        brier_score           : float
        log_loss              : float
    """
    try:
        from sklearn.metrics import brier_score_loss, log_loss as sk_log_loss
        from sklearn.calibration import calibration_curve

        y_true_arr = np.asarray(y_true)
        y_proba_arr = np.asarray(y_proba, dtype=float)

        if pos_label is not None:
            y_binary = (y_true_arr == pos_label).astype(int)
        else:
            y_binary = y_true_arr.astype(int)

        fraction_of_positives, mean_predicted = calibration_curve(
            y_binary, y_proba_arr, n_bins=n_bins, strategy="uniform"
        )

        bins = list(np.linspace(1.0 / n_bins, 1.0, n_bins))

        # Per-bin counts
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        bin_indices = np.digitize(y_proba_arr, bin_edges[1:-1])
        counts = [int(np.sum(bin_indices == i)) for i in range(n_bins)]

        # Scalar metrics
        bs = float(brier_score_loss(y_binary, y_proba_arr))
        ll = float(sk_log_loss(y_binary, y_proba_arr, labels=[0, 1]))

        return {
            "bins": [round(b, 3) for b in bins],
            "fraction_of_positives": [round(float(f), 4) for f in fraction_of_positives],
            "mean_predicted": [round(float(m), 4) for m in mean_predicted],
            "counts": counts,
            "brier_score": round(bs, 6),
            "log_loss": round(ll, 6),
        }

    except Exception as exc:
        logger.error("[calibration] generate_reliability_diagram failed: %s", exc)
        return {
            "bins": [],
            "fraction_of_positives": [],
            "mean_predicted": [],
            "counts": [],
            "brier_score": None,
            "log_loss": None,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Full evaluation summary
# ---------------------------------------------------------------------------

def evaluate_calibration(model, X_test, y_test) -> dict:
    """
    Runs the model on X_test and returns a calibration + accuracy summary.

    Parameters
    ----------
    model  : fitted sklearn-compatible classifier with predict_proba
    X_test : array-like, test features (already scaled)
    y_test : array-like, true labels

    Returns
    -------
    dict with keys:
        accuracy    : float
        log_loss    : float
        brier_score : float  (macro-average over classes)
        n_samples   : int
        classes     : list   — class labels in the order used by predict_proba
        per_class_brier : dict[str, float]
    """
    try:
        from sklearn.metrics import (
            accuracy_score,
            log_loss as sk_log_loss,
            brier_score_loss,
        )

        y_true_arr = np.asarray(y_test)
        y_proba = model.predict_proba(X_test)
        y_pred = model.predict(X_test)

        acc = float(accuracy_score(y_true_arr, y_pred))
        ll = float(sk_log_loss(y_true_arr, y_proba))

        classes = list(model.classes_) if hasattr(model, "classes_") else list(range(y_proba.shape[1]))
        per_class_brier: dict[str, float] = {}
        brier_scores = []
        for idx, cls in enumerate(classes):
            y_bin = (y_true_arr == cls).astype(int)
            bs = float(brier_score_loss(y_bin, y_proba[:, idx]))
            per_class_brier[str(cls)] = round(bs, 6)
            brier_scores.append(bs)

        macro_brier = float(np.mean(brier_scores))

        return {
            "accuracy": round(acc, 4),
            "log_loss": round(ll, 6),
            "brier_score": round(macro_brier, 6),
            "n_samples": int(len(y_true_arr)),
            "classes": [str(c) for c in classes],
            "per_class_brier": per_class_brier,
        }

    except Exception as exc:
        logger.error("[calibration] evaluate_calibration failed: %s", exc)
        return {
            "accuracy": None,
            "log_loss": None,
            "brier_score": None,
            "n_samples": 0,
            "error": str(exc),
        }
