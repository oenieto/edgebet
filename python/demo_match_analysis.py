"""
Edgebet — demo de análisis real sobre un partido concreto.

Uso:
    cd python && source .venv/bin/activate
    python demo_match_analysis.py

Cómo funciona:
1. Descarga temporadas EPL reales (football-data.co.uk)
2. Calcula ELO a lo largo de todo el histórico (rating final = estado actual)
3. Extrae forma reciente (últimos 5) de local y visitante
4. Deriva probabilidades "ML baseline" con ELO (hasta que entrenemos XGBoost)
5. Normaliza las cuotas de Bet365 a probabilidades implícitas
6. Llama a Claude (claude-sonnet-4-20250514) con el SYSTEM_PROMPT de Edgebet
7. Imprime el pick final en JSON
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from data.loader import FootballDataLoader, DataCleaner
from features.elo import FootballELO
from deterministic_pick import generate_pick


HOME = "Man City"
AWAY = "Arsenal"
LEAGUE = "Premier League"

# Cuotas de referencia tipo Bet365 para Man City (local) vs Arsenal.
# Reemplazar por las reales del día si se tienen.
BET365_H = 2.00
BET365_D = 3.60
BET365_A = 3.80


def compute_team_form(df, team: str, n: int = 5) -> dict:
    """Últimos `n` partidos del equipo — promedia goles, tiros, forma."""
    mask = (df["HomeTeam"] == team) | (df["AwayTeam"] == team)
    recent = df[mask].sort_values("Date").tail(n)

    gf, ga, shots, sot, pts = [], [], [], [], []
    for _, row in recent.iterrows():
        is_home = row["HomeTeam"] == team
        gf.append(row["FTHG"] if is_home else row["FTAG"])
        ga.append(row["FTAG"] if is_home else row["FTHG"])
        shots.append(row.get("HS", 0) if is_home else row.get("AS", 0))
        sot.append(row.get("HST", 0) if is_home else row.get("AST", 0))
        if is_home:
            pts.append(3 if row["FTR"] == "H" else (1 if row["FTR"] == "D" else 0))
        else:
            pts.append(3 if row["FTR"] == "A" else (1 if row["FTR"] == "D" else 0))

    n_played = len(gf) or 1
    return {
        "avg_GF": sum(gf) / n_played,
        "avg_GA": sum(ga) / n_played,
        "avg_Shots": sum(shots) / n_played,
        "avg_SoT": sum(sot) / n_played,
        "Form": sum(pts) / n_played,
        "matches_counted": n_played,
    }


def elo_to_3way_probs(p_home_raw: float, base_draw: float = 0.26) -> dict:
    """
    ELO da P(home beats away) 2-vías. Repartimos el residuo
    asumiendo base_draw% de empates típicos en EPL.
    """
    home = p_home_raw * (1 - base_draw)
    away = (1 - p_home_raw) * (1 - base_draw)
    return {"home": home, "draw": base_draw, "away": away}


def normalize_bookmaker_odds(odds_h: float, odds_d: float, odds_a: float) -> dict:
    """Probs implícitas normalizadas (quita el margen del bookie)."""
    inv = [1 / odds_h, 1 / odds_d, 1 / odds_a]
    total = sum(inv)
    return {"home": inv[0] / total, "draw": inv[1] / total, "away": inv[2] / total}


def main():
    print("=" * 70)
    print(f"EDGEBET — análisis real: {HOME} vs {AWAY}")
    print("=" * 70)

    # 1. Datos reales — últimas 2 temporadas EPL
    print("\n[1/5] Descargando datos reales football-data.co.uk…")
    loader = FootballDataLoader(seasons=["2526", "2425"], leagues=["E0"])
    raw = loader.load_all()
    if raw.empty:
        print("❌ No se pudieron descargar datos.")
        return
    clean = DataCleaner.clean(raw)
    print(f"Partidos limpios: {len(clean)}")

    # Verificación de nombres
    teams = set(clean["HomeTeam"].unique()) | set(clean["AwayTeam"].unique())
    if HOME not in teams:
        print(f"⚠️ '{HOME}' no está en los datos. Sugerencias:",
              [t for t in teams if "man" in t.lower() or "city" in t.lower()])
        return
    if AWAY not in teams:
        print(f"⚠️ '{AWAY}' no está en los datos. Sugerencias:",
              [t for t in teams if "arsenal" in t.lower()])
        return

    # 2. ELO sobre todo el histórico
    print("\n[2/5] Calculando ELO sobre todo el histórico…")
    elo = FootballELO(k=32, home_advantage=65)
    elo.compute_elo_features(clean)

    r_home = elo.get_rating(HOME)
    r_away = elo.get_rating(AWAY)
    p_home_raw = elo.expected_score(r_home + elo.home_advantage, r_away)
    print(f"ELO actual — {HOME}: {r_home:.0f} | {AWAY}: {r_away:.0f}")
    print(f"P({HOME} gana) vía ELO 2-way: {p_home_raw:.1%}")

    # 3. Forma reciente
    print("\n[3/5] Forma reciente (últimos 5 partidos)…")
    home_form = compute_team_form(clean, HOME)
    away_form = compute_team_form(clean, AWAY)
    print(f"{HOME}: forma={home_form['Form']:.2f} pts/partido, "
          f"GF={home_form['avg_GF']:.2f}, GA={home_form['avg_GA']:.2f}")
    print(f"{AWAY}: forma={away_form['Form']:.2f} pts/partido, "
          f"GF={away_form['avg_GF']:.2f}, GA={away_form['avg_GA']:.2f}")

    # 4. Probabilidades 3-way
    ml_probs = elo_to_3way_probs(p_home_raw)
    bookmaker_probs = normalize_bookmaker_odds(BET365_H, BET365_D, BET365_A)

    print("\n[4/5] Probabilidades consolidadas (3-way)")
    print(f"  ML baseline (ELO): H={ml_probs['home']:.1%} D={ml_probs['draw']:.1%} A={ml_probs['away']:.1%}")
    print(f"  Bet365 normalizado: H={bookmaker_probs['home']:.1%} D={bookmaker_probs['draw']:.1%} A={bookmaker_probs['away']:.1%}")
    print(f"  (Cuotas usadas: {BET365_H} / {BET365_D} / {BET365_A})")

    # 5. Pick determinista (sin Claude)
    print("\n[5/5] Generando pick determinista (EV + Kelly fraccional)…")
    bookmaker_odds = {"H": BET365_H, "D": BET365_D, "A": BET365_A}
    pick = generate_pick(
        home_team=HOME,
        away_team=AWAY,
        ml_probs=ml_probs,
        bookmaker_probs=bookmaker_probs,
        bookmaker_odds=bookmaker_odds,
        home_form=home_form,
        away_form=away_form,
    )

    # 6. Capa Claude opcional — solo si hay créditos disponibles
    claude_narrative = None
    try:
        from claude_analysis import analyze_match  # import tardío
        print("\n[+] Intentando capa Claude para narrativa…")
        claude_narrative = analyze_match(
            home_team=HOME,
            away_team=AWAY,
            league=LEAGUE,
            home_form=home_form,
            away_form=away_form,
            ml_probs=ml_probs,
            bookmaker_probs=bookmaker_probs,
            polymarket_probs=None,
        )
    except Exception as e:
        msg = str(e)
        if "credit balance" in msg.lower():
            print("  ⚠️ Sin créditos Anthropic — usando solo pick determinista.")
        else:
            print(f"  ⚠️ Claude falló ({type(e).__name__}) — usando solo pick determinista.")

    print("\n" + "=" * 70)
    print("PICK FINAL DE EDGEBET")
    print("=" * 70)
    print(json.dumps(pick, indent=2, ensure_ascii=False))

    if claude_narrative:
        print("\n--- Capa Claude (narrativa) ---")
        print(json.dumps(claude_narrative, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
