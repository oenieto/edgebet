import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, log_loss, classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier
import pickle
from datetime import datetime
from pathlib import Path


PREDICTOR_FEATURE_COLUMNS = [
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


def prepare_model_data(df: pd.DataFrame, use_predictor_cols: bool = True, target_col: str = "Result") -> tuple:
    """
    Si use_predictor_cols=True: usa el subset exacto que consume el predictor en runtime.
    Así el modelo entrenado y el inferido viven sobre el mismo espacio de features.
    """
    if use_predictor_cols:
        available = [c for c in PREDICTOR_FEATURE_COLUMNS if c in df.columns]
        if "diff_xG_proxy" in PREDICTOR_FEATURE_COLUMNS and "diff_xG_proxy" not in df.columns:
            if "home_xG_proxy" in df.columns and "away_xG_proxy" in df.columns:
                df = df.copy()
                df["diff_xG_proxy"] = df["home_xG_proxy"] - df["away_xG_proxy"]
                available.append("diff_xG_proxy")
        feature_cols = available
    else:
        feature_cols = [c for c in df.columns if c.startswith((
            "home_", "away_", "diff_", "norm_prob_", "odds_spread",
            "elo_", "h2h_", "home_rest", "away_rest", "rest_advantage",
            "home_fatigued", "away_fatigued", "is_midweek",
            "home_xG", "away_xG", "kl_div", "divergence_", "abs_div",
            "blended_prob_", "triple_blend_",
        ))]
    X = df[feature_cols].copy().fillna(df[feature_cols].median())
    y = df[target_col].copy()
    print(f"Features: {X.shape[1]} | Matches: {X.shape[0]}")
    print(f"Class balance: {y.value_counts().to_dict()}")
    return X, y, feature_cols


def train_with_cv(X: pd.DataFrame, y: pd.Series) -> dict:
    """TimeSeriesSplit cross-validation — never random split."""
    tscv = TimeSeriesSplit(n_splits=5)
    scaler = StandardScaler()

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, C=0.5),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=10, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8,
                                  colsample_bytree=0.8, random_state=42, eval_metric="mlogloss"),
    }

    results = {}
    for name, model in models.items():
        fold_acc, fold_ll = [], []
        for train_idx, test_idx in tscv.split(X):
            X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
            y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
            X_tr_s = scaler.fit_transform(X_tr)
            X_te_s = scaler.transform(X_te)
            model.fit(X_tr_s, y_tr)
            preds = model.predict(X_te_s)
            proba = model.predict_proba(X_te_s)
            fold_acc.append(accuracy_score(y_te, preds))
            fold_ll.append(log_loss(y_te, proba))
        results[name] = {
            "accuracy_mean": np.mean(fold_acc),
            "accuracy_std": np.std(fold_acc),
            "log_loss_mean": np.mean(fold_ll),
            "log_loss_std": np.std(fold_ll),
        }
        print(f"{name}: accuracy={results[name]['accuracy_mean']:.4f} ± {results[name]['accuracy_std']:.4f}")
    return results


def build_and_save_ensemble(X: pd.DataFrame, y: pd.Series, save_dir: str | None = None, prefix: str = "ensemble", target_names: list[str] | None = None) -> tuple:
    if save_dir is None:
        save_dir = str(Path(__file__).resolve().parent)
    """Build ensemble, evaluate on holdout, save to disk."""
    scaler = StandardScaler()
    ensemble = VotingClassifier(
        estimators=[
            ("lr", LogisticRegression(max_iter=1000, C=0.5)),
            ("rf", RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)),
            ("xgb", XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                                   random_state=42, eval_metric="mlogloss")),
        ],
        voting="soft", weights=[1, 1, 2],
    )

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    ensemble.fit(X_train_s, y_train)

    preds = ensemble.predict(X_test_s)
    proba = ensemble.predict_proba(X_test_s)
    acc = accuracy_score(y_test, preds)
    ll = log_loss(y_test, proba)
    print(f"\n{prefix.capitalize()} — Accuracy: {acc:.4f} | Log Loss: {ll:.4f}")
    
    if target_names is None:
        target_names = ["Away","Draw","Home"] if len(np.unique(y)) == 3 else ["Under", "Over"]
    print(classification_report(y_test, preds, target_names=target_names))

    Path(save_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    with open(f"{save_dir}/{prefix}_{ts}.pkl", "wb") as f:
        pickle.dump(ensemble, f)
    with open(f"{save_dir}/scaler_{prefix}_{ts}.pkl", "wb") as f:
        pickle.dump(scaler, f)
    # Persistimos el orden exacto de columnas para que el predictor lo replique
    with open(f"{save_dir}/feature_columns_{prefix}.txt", "w") as f:
        f.write("\n".join(list(X.columns)))
    print(f"Saved: {prefix}_{ts}.pkl + scaler_{prefix}_{ts}.pkl + feature_columns_{prefix}.txt")
    return ensemble, scaler


class WalkForwardBacktest:
    """Correct time-series backtesting — no future leakage."""

    def __init__(self, initial_train_size: int = 500, step_size: int = 38):
        self.initial_train_size = initial_train_size
        self.step_size = step_size

    def run(self, X: pd.DataFrame, y: pd.Series) -> dict:
        all_preds, all_proba, all_true = [], [], []

        for start in range(self.initial_train_size, len(X) - self.step_size, self.step_size):
            end = start + self.step_size
            X_train, y_train = X.iloc[:start], y.iloc[:start]
            X_test, y_test = X.iloc[start:end], y.iloc[start:end]

            scaler = StandardScaler()
            model = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                                   random_state=42, eval_metric="mlogloss")
            model.fit(scaler.fit_transform(X_train), y_train)
            preds = model.predict(scaler.transform(X_test))
            proba = model.predict_proba(scaler.transform(X_test))
            all_preds.extend(preds)
            all_proba.extend(proba)
            all_true.extend(y_test.values)

        all_preds = np.array(all_preds)
        all_proba = np.array(all_proba)
        all_true = np.array(all_true)

        results = {
            "total_predictions": len(all_preds),
            "accuracy": accuracy_score(all_true, all_preds),
            "log_loss": log_loss(all_true, all_proba),
        }
        print(f"Walk-Forward: {results['total_predictions']} predictions | "
              f"accuracy={results['accuracy']:.4f} | log_loss={results['log_loss']:.4f}")
        return results