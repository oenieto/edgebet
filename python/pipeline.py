"""
Edgebet ML Pipeline — Orquestador principal
Ejecuta: python python/pipeline.py
"""
from data.loader import FootballDataLoader, DataCleaner
from features.engineering import FeatureEngineer
from features.elo import FootballELO
from features.polymarket import PolymarketClient, TripleLayerFeatures
from models.train import prepare_model_data, train_with_cv, build_and_save_ensemble, WalkForwardBacktest
from claude_analysis import analyze_match


def run_full_pipeline(
    seasons: list[str] = ["2425", "2324", "2223", "2122", "2021"],
    leagues: list[str] = ["E0", "SP1", "D1", "I1", "F1"],
    run_backtest: bool = True,
):
    print("=" * 60)
    print("EDGEBET ML PIPELINE")
    print("=" * 60)

    # 1. Load data
    print("\n[1/6] Loading data...")
    loader = FootballDataLoader(seasons=seasons, leagues=leagues)
    raw = loader.load_all()

    # 2. Clean
    print("\n[2/6] Cleaning data...")
    clean = DataCleaner.clean(raw)
    print(f"Clean matches: {len(clean)}")

    # 3. Feature engineering
    print("\n[3/6] Feature engineering...")
    eng = FeatureEngineer(window=5)
    featured = eng.build_match_features(clean)
    featured = eng.add_odds_features(featured)
    featured = eng.compute_xg_proxy(featured)
    featured["diff_xG_proxy"] = featured["home_xG_proxy"] - featured["away_xG_proxy"]
    featured = eng.compute_fatigue_features(featured)
    featured = eng.compute_h2h_features(featured)

    # 4. ELO ratings
    print("\n[4/6] Computing ELO ratings...")
    elo = FootballELO(k=32, home_advantage=65)
    featured = elo.compute_elo_features(featured)
    print("Top 5 teams by ELO:")
    for team, rating in elo.top_teams(5):
        print(f"  {team:25s} {rating:.0f}")

    # 5. Train models (Moneyline)
    print("\n[5/6] Training models (Moneyline)...")
    X, y, feature_names = prepare_model_data(featured, target_col="Result")
    cv_results = train_with_cv(X, y)
    ensemble, scaler = build_and_save_ensemble(X, y, prefix="ensemble_ml")
    
    print("\n[5.5/6] Training models (Over/Under 2.5)...")
    if "Over2_5" in featured.columns:
        X_ou, y_ou, _ = prepare_model_data(featured.dropna(subset=["Over2_5"]), target_col="Over2_5")
        cv_ou = train_with_cv(X_ou, y_ou)
        ensemble_ou, scaler_ou = build_and_save_ensemble(X_ou, y_ou, prefix="ensemble_ou", target_names=["Under", "Over"])

    # 6. Backtest
    if run_backtest:
        print("\n[6/6] Walk-forward backtest...")
        backtester = WalkForwardBacktest(initial_train_size=500, step_size=38)
        backtest_results = backtester.run(X, y)
        print(f"Backtest accuracy: {backtest_results['accuracy']:.4f}")

    print("\n✓ Pipeline complete")
    return ensemble, scaler, featured


def predict_match(
    home_team: str,
    away_team: str,
    league: str,
    home_form: dict,
    away_form: dict,
    bookmaker_probs: dict,
    polymarket_probs: dict | None = None,
    ensemble=None,
    scaler=None,
) -> dict:
    """
    Generate a complete pick for a single upcoming match.
    Combines ML prediction + Polymarket + Claude analysis.
    """
    # Get ML probabilities (placeholder — integrate with trained model)
    # In production: extract features for this match and call ensemble.predict_proba()
    ml_probs = {
        "home": home_form.get("Form", 1.5) / 3.0,
        "draw": 0.25,
        "away": away_form.get("Form", 1.0) / 3.0,
    }
    # Normalize
    total = sum(ml_probs.values())
    ml_probs = {k: v/total for k, v in ml_probs.items()}

    # Compute divergence features
    if polymarket_probs:
        divergence = TripleLayerFeatures.compute_divergence_features(
            bookmaker_probs, polymarket_probs, ml_probs
        )
    else:
        divergence = {}

    # Get Claude analysis
    analysis = analyze_match(
        home_team=home_team,
        away_team=away_team,
        league=league,
        home_form=home_form,
        away_form=away_form,
        ml_probs=ml_probs,
        bookmaker_probs=bookmaker_probs,
        polymarket_probs=polymarket_probs,
    )

    return {
        "match": f"{home_team} vs {away_team}",
        "league": league,
        "ml_probs": ml_probs,
        "bookmaker_probs": bookmaker_probs,
        "polymarket_probs": polymarket_probs,
        "divergence_features": divergence,
        "claude_analysis": analysis,
    }


if __name__ == "__main__":
    run_full_pipeline()