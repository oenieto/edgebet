"""
Servicio que produce picks reales para el endpoint /picks/today.

Pipeline por fixture:
  1. Cargar histórico real (fast_loader) → ELO + forma por equipo.
  2. ML probs desde ensemble entrenado (fallback a ELO si no hay modelo).
  3. Polymarket live: búsqueda fuzzy del mercado correspondiente (si existe).
  4. Bet365: cuotas reales si vienen en el fixture; sintéticas perturbadas si no.
  5. Triple-layer blend 0.40 * ML + 0.35 * Polymarket + 0.25 * Bet365.
  6. Pick determinista (EV + Kelly fraccional) sobre el blend.
  7. Claude narrativa (cacheada) solo si el pick es recomendado.
  8. Tier según magnitud del edge.
"""
from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

# Permitir imports desde python/ ANTES de importar deterministic_pick (vive en /python)
_PY_ROOT = Path(__file__).resolve().parent.parent
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

# Top-level imports — promovidos desde el cuerpo de funciones tras detectar
# TimeoutError (Errno 60) en imports lazy bajo carga de I/O. Ahora todo se
# resuelve en startup, no por request.
from api.db import connect
from api import predictor
from api.claude_narrative import generate_narrative, merge_narrative_into_pick
from api.openfootball_loader import load_fixtures_of, load_history_of
from api.fast_loader import compute_elo, compute_team_form
from api.team_logos import logo_url as _team_logo_url
from api.polymarket_live import find_match_probs
from api.poisson_markets import build_market_outcomes
from api.odds_provider import (
    fetch_league_odds,
    find_odds_for_match,
    is_configured as odds_is_configured,
)
from api.champions_league import list_fixtures as list_cl_fixtures, load_cl_context
from api.world_cup import list_fixtures as list_wc_fixtures, load_wc_context
from deterministic_pick import generate_pick

PREDICTION_MAP = {"H": "home", "D": "draw", "A": "away"}


def _logo_url(team_name: str) -> str | None:
    """Wrapper resiliente — devuelve None si el mapeo falla por cualquier razón."""
    try:
        return _team_logo_url(team_name)
    except Exception:
        return None



@dataclass
class LeagueConfig:
    slug: str
    name: str
    fd_code: str
    seasons: tuple[str, ...]
    featured: tuple[tuple[str, str], ...]
    logo: str | None = None


LEAGUES: dict[str, LeagueConfig] = {
    "premier-league": LeagueConfig(
        slug="premier-league",
        name="Premier League",
        fd_code="E0",
        seasons=("2425", "2324"),
        featured=(("Man City", "Arsenal"), ("Liverpool", "Chelsea")),
        logo="https://a.espncdn.com/i/leaguelogos/soccer/500/23.png",
    ),
    "la-liga": LeagueConfig(
        slug="la-liga",
        name="La Liga",
        fd_code="SP1",
        seasons=("2425", "2324"),
        featured=(("Real Madrid", "Barcelona"), ("Atletico Madrid", "Sevilla")),
        logo="https://a.espncdn.com/i/leaguelogos/soccer/500/15.png",
    ),
    "bundesliga": LeagueConfig(
        slug="bundesliga",
        name="Bundesliga",
        fd_code="D1",
        seasons=("2425", "2324"),
        featured=(("Bayern Munich", "Dortmund"), ("Leverkusen", "RB Leipzig")),
        logo="https://a.espncdn.com/i/leaguelogos/soccer/500/10.png",
    ),
    "serie-a": LeagueConfig(
        slug="serie-a",
        name="Serie A",
        fd_code="I1",
        seasons=("2425", "2324"),
        featured=(("Inter", "Juventus"), ("Napoli", "Milan")),
        logo="https://a.espncdn.com/i/leaguelogos/soccer/500/12.png",
    ),
    "ligue-1": LeagueConfig(
        slug="ligue-1",
        name="Ligue 1",
        fd_code="F1",
        seasons=("2425", "2324"),
        featured=(("Paris SG", "Marseille"), ("Monaco", "Lille")),
        logo="https://a.espncdn.com/i/leaguelogos/soccer/500/9.png",
    ),
    "champions-league": LeagueConfig(
        slug="champions-league",
        name="UEFA Champions League",
        fd_code="UCL",  # marcador — no se baja de football-data.co.uk
        seasons=(),     # sin histórico propio; se cruzan las 5 ligas top
        featured=(),
        logo="https://a.espncdn.com/i/leaguelogos/soccer/500/2.png",
    ),
    "liga-mx": LeagueConfig(
        slug="liga-mx",
        name="Liga MX",
        fd_code="MX1",  # no existe en football-data.co.uk; usamos openfootball mx.1
        seasons=("2425",),
        featured=(("America", "Guadalajara"), ("Tigres UANL", "Monterrey")),
        logo="https://a.espncdn.com/i/leaguelogos/soccer/500/13.png",
    ),
    "fifa-world-cup": LeagueConfig(
        slug="fifa-world-cup",
        name="FIFA World Cup 2026",
        fd_code="WC",
        seasons=(),
        featured=(("Argentina", "France"), ("Spain", "England")),
        logo="https://a.espncdn.com/i/leaguelogos/soccer/500/4.png",
    ),
}


def _synth_bookmaker_odds(our_probs: dict, seed: int) -> tuple[dict, dict[str, float]]:
    rng = random.Random(seed)
    perturbations = {
        "home": rng.uniform(-0.08, 0.08),
        "draw": rng.uniform(-0.04, 0.04),
        "away": rng.uniform(-0.08, 0.08),
    }
    raw = {k: max(0.05, min(0.90, our_probs[k] + perturbations[k])) for k in our_probs}
    total = sum(raw.values())
    norm = {k: v / total for k, v in raw.items()}
    margin = 1.05
    odds = {
        "H": round(1 / (norm["home"] * margin), 2),
        "D": round(1 / (norm["draw"] * margin), 2),
        "A": round(1 / (norm["away"] * margin), 2),
    }
    inv = [1 / odds["H"], 1 / odds["D"], 1 / odds["A"]]
    tot_inv = sum(inv)
    bk_probs = {
        "home": inv[0] / tot_inv,
        "draw": inv[1] / tot_inv,
        "away": inv[2] / tot_inv,
    }
    return bk_probs, odds


def _real_bookmaker_from_fixture(fixture: dict) -> tuple[dict, dict[str, float]] | None:
    """Cuotas reales si vienen en el CSV de fixtures (columnas B365*)."""
    try:
        h = float(fixture.get("B365H", ""))
        d = float(fixture.get("B365D", ""))
        a = float(fixture.get("B365A", ""))
    except (TypeError, ValueError):
        return None
    if not (h > 1.01 and d > 1.01 and a > 1.01):
        return None
    inv = [1 / h, 1 / d, 1 / a]
    total = sum(inv)
    probs = {"home": inv[0] / total, "draw": inv[1] / total, "away": inv[2] / total}
    odds = {"H": round(h, 2), "D": round(d, 2), "A": round(a, 2)}
    return probs, odds


def _tier_for_edge(edge_pp: float, ev_pct: float, sources_agree: bool) -> str:
    """
    Tier logic:
      vip = edge muy alto Y todas las fuentes coinciden en favorito (alta convicción)
      premium = edge/EV decente
      free = resto
    """
    if sources_agree and (ev_pct >= 15.0 or edge_pp >= 8.0):
        return "vip"
    if ev_pct >= 8.0 or edge_pp >= 5.0:
        return "premium"
    return "free"


_teams_cache: dict[str, dict] = {}

def get_teams_dict() -> dict[str, dict]:
    global _teams_cache
    if not _teams_cache:
        try:
            with connect() as cur:
                cur.execute("SELECT name, country_id, entity_type FROM teams")
                rows = cur.fetchall()
                for r in rows:
                    _teams_cache[r["name"]] = {"country_id": r["country_id"], "entity_type": r["entity_type"]}
        except Exception as exc:
            print(f"[picks_service] DB error caching teams: {exc}")
    return _teams_cache

def infer_match_icon(home_team: str, away_team: str) -> str:
    teams_db = get_teams_dict()
    home = teams_db.get(home_team)
    away = teams_db.get(away_team)
    
    if not home or not away:
        return "⭐"
        
    flags = {"ES": "🇪🇸", "EN": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "IT": "🇮🇹", "DE": "🇩🇪", "FR": "🇫🇷", "MX": "🇲🇽", "AR": "🇦🇷"}
    
    if home["entity_type"] == "Selección" and away["entity_type"] == "Selección":
        return "🏆"
    elif home["entity_type"] == "Club" and away["entity_type"] == "Club":
        if home["country_id"] == away["country_id"]:
            return flags.get(home["country_id"], "📍")
        else:
            return "⭐"
            
    return "⭐"


@lru_cache(maxsize=16)
def _load_league(slug: str):
    cfg = LEAGUES[slug]
    if slug == "champions-league":
        matches, ratings = load_cl_context()
        return matches, ratings, cfg
    if slug == "fifa-world-cup":
        matches, ratings = load_wc_context()
        return matches, ratings, cfg
    # openfootball como fuente primaria (GitHub, siempre reachable)
    matches = load_history_of(slug)
    ratings = compute_elo(matches, k=32, home_advantage=65)
    return matches, ratings, cfg


def _attach_odds(outcome: dict, price: float, margin: float | None = None) -> None:
    """Inyecta odds + market_prob + edge + EV en un outcome dado."""
    if price is None or price <= 1.0:
        return
    if margin is None or margin <= 0:
        market_prob = 1.0 / price  # asume margen ya incluido
    else:
        market_prob = (1.0 / price) / margin  # quita margen del par/triple
    our_prob = outcome["our_prob_pct"] / 100.0
    outcome["odds"] = round(float(price), 2)
    outcome["market_prob_pct"] = round(market_prob * 100, 2)
    outcome["edge_pp"] = round((our_prob - market_prob) * 100, 2)
    outcome["ev_pct"] = round((our_prob * price - 1.0) * 100, 2)


def _apply_real_odds_to_markets(markets: dict, odds_entry: dict | None) -> dict:
    """
    Inyecta cuotas reales (y EV/edge derivados) en cada outcome de cada mercado.

    Coverage:
      - OU goles totales: empareja línea (1.5/2.5/3.5/...) con `totals_by_line`.
      - DC (1X/X2/12): cuotas derivadas matemáticamente de h2h.
      - Spreads (handicaps): empareja línea con `spreads_by_line`.
      - BTTS / team_totals: solo si el tier paga additional markets — sino
        quedan info-only con nuestra prob Poisson.

    Outcomes sin odds reales quedan con `odds=None` y el frontend muestra
    solo `our_prob_pct`.
    """
    if not odds_entry or not markets:
        return markets

    totals_by_line: dict = odds_entry.get("totals_by_line") or {}
    spreads_by_line: dict = odds_entry.get("spreads_by_line") or {}
    dc_odds: dict | None = odds_entry.get("double_chance")

    # OU — key "over_2_5" → line "2.5"
    for outcome in markets.get("ou_outcomes", []):
        key = outcome["outcome"]
        parts = key.split("_")
        if len(parts) < 3 or parts[0] not in ("over", "under"):
            continue
        side = parts[0]
        try:
            line = f"{float(parts[1] + '.' + parts[2]):.1f}"
        except ValueError:
            continue
        line_entry = totals_by_line.get(line)
        if not line_entry or "over" not in line_entry or "under" not in line_entry:
            continue
        price = line_entry.get(side)
        margin = 1.0 / line_entry["over"] + 1.0 / line_entry["under"]
        _attach_odds(outcome, price, margin)

    # DC — usa cuotas derivadas (sin margen — ya viene con el del h2h)
    if dc_odds:
        for outcome in markets.get("dc_outcomes", []):
            price = dc_odds.get(outcome["outcome"])
            _attach_odds(outcome, price)

    # Spreads — key "home_-1.5" / "away_-1.5" donde line_key siempre va desde
    # la perspectiva del home (igual que spreads_by_line). Para el outcome del
    # away, leemos el campo "away" de la misma entrada — representa "away
    # gana el handicap inverso" matemáticamente.
    for outcome in markets.get("spread_outcomes", []):
        key = outcome["outcome"]
        if "_" not in key:
            continue
        side, line_key = key.split("_", 1)
        if side not in ("home", "away"):
            continue
        line_entry = spreads_by_line.get(line_key)
        if not line_entry or "home" not in line_entry or "away" not in line_entry:
            continue
        price = line_entry.get(side)
        margin = 1.0 / line_entry["home"] + 1.0 / line_entry["away"]
        _attach_odds(outcome, price, margin)

    # BTTS / team_totals: si el provider devuelve esos mercados (tier paid)
    # los emparejamos. En tier free quedan informativos con prob Poisson.
    btts_yes = odds_entry.get("btts_yes")
    btts_no = odds_entry.get("btts_no")
    if btts_yes and btts_no:
        margin_btts = 1.0 / btts_yes + 1.0 / btts_no
        for outcome in markets.get("btts_outcomes", []):
            price = btts_yes if outcome["outcome"] == "yes" else btts_no
            _attach_odds(outcome, price, margin_btts)

    return markets


def _sources_agree_flag(ml: dict, bk: dict, poly: dict | None) -> bool:
    ml_fav = max(ml, key=ml.get)
    bk_fav = max(bk, key=bk.get)
    if poly is None:
        return ml_fav == bk_fav
    poly_fav = max(poly, key=poly.get)
    return ml_fav == bk_fav == poly_fav


def _build_pick_for_match(
    slug: str,
    home_team: str,
    away_team: str,
    seed: int,
    fixture_row: dict | None = None,
) -> dict | None:
    try:
        matches, ratings, cfg = _load_league(slug)
    except Exception as exc:
        print(f"[picks_service] no pude cargar liga {slug}: {exc}")
        return None

    home_form = compute_team_form(matches, home_team)
    away_form = compute_team_form(matches, away_team)

    # Bookmaker: prioridad 1) CSV fixture (B365), 2) The Odds API live, 3) sintéticas.
    bookmaker: tuple[dict, dict] | None = None
    bookmaker_source = "synthetic"
    if fixture_row:
        bookmaker = _real_bookmaker_from_fixture(fixture_row)
        if bookmaker is not None:
            bookmaker_source = "bet365"

    if bookmaker is None and odds_is_configured():
        try:
            entry = find_odds_for_match(home_team, away_team, slug)
            if entry:
                h = entry["h2h"].get("home")
                d = entry["h2h"].get("draw")
                a = entry["h2h"].get("away")
                if h and d and a and h > 1.01 and d > 1.01 and a > 1.01:
                    inv = [1 / h, 1 / d, 1 / a]
                    total = sum(inv)
                    probs = {"home": inv[0] / total, "draw": inv[1] / total, "away": inv[2] / total}
                    odds_dict = {"H": round(h, 2), "D": round(d, 2), "A": round(a, 2)}
                    bookmaker = (probs, odds_dict)
                    bookmaker_source = entry.get("bookmaker") or "the-odds-api"
        except Exception as exc:
            print(f"[picks_service] odds API h2h falló para {home_team}-{away_team}: {exc}")

    elo_probs_preview = predictor.baseline_elo_probs(
        ratings.get(home_team, 1500.0), ratings.get(away_team, 1500.0)
    )
    if bookmaker is None:
        bk_probs, bk_odds = _synth_bookmaker_odds(elo_probs_preview, seed=seed)
    else:
        bk_probs, bk_odds = bookmaker

    # ML probs (ensemble o ELO fallback, o Poisson xG)
    import os
    pred_method = (os.environ.get("PREDICTION_METHOD") or "ensemble").lower()
    if pred_method == "poisson":
        from api.poisson_predictor import predict_poisson_probs
        ml_probs = predict_poisson_probs(home_form, away_form)
        ml_source = "poisson"
    else:
        ml_probs, ml_source = predictor.predict_ml_probs(
            home_team=home_team,
            away_team=away_team,
            matches=matches,
            elo_ratings=ratings,
            home_form=home_form,
            away_form=away_form,
            bookmaker_probs=bk_probs,
        )

    # Polymarket live (puede devolver None si no hay mercado)
    poly_probs_dict: dict | None = None
    poly_meta: dict | None = None
    try:
        poly_pick = find_match_probs(home_team, away_team)
        if poly_pick:
            poly_probs_dict = {
                "home": poly_pick.home,
                "draw": poly_pick.draw,
                "away": poly_pick.away,
            }
            poly_meta = {
                "liquidity": poly_pick.liquidity,
                "volume_24h": poly_pick.volume_24h,
                "market_slug": poly_pick.market_slug,
                "match_confidence": poly_pick.confidence,
            }
    except Exception as exc:
        print(f"[picks_service] polymarket fallo: {exc}")

    # Triple blend
    blended = predictor.triple_layer_blend(
        ml_probs=ml_probs,
        bookmaker_probs=bk_probs,
        polymarket_probs=poly_probs_dict,
    )

    # Pick determinista sobre el blend (más robusto que usar solo ML)
    pick = generate_pick(
        home_team=home_team,
        away_team=away_team,
        ml_probs=blended,
        bookmaker_probs=bk_probs,
        bookmaker_odds=bk_odds,
        home_form=home_form,
        away_form=away_form,
    )

    sources_agree = _sources_agree_flag(ml_probs, bk_probs, poly_probs_dict)

    # Sin línea real de mercado, el edge/EV contra odds sintéticas es ruido:
    # la capa ML (ensemble) diverge de la ELO-perturbada por diseño y fabrica
    # edges absurdos (>100% EV). En ese caso el pick es solo predicción del
    # modelo, no recomendación de apuesta.
    market_verified = bookmaker_source != "synthetic"
    if market_verified:
        edge_pp = pick["edge_pp"]
        ev_pct = pick["ev_pct"]
        odds_display = pick["bookmaker_odds"]
        stake = pick["suggested_stake_pct"]
        tier = _tier_for_edge(abs(edge_pp), ev_pct, sources_agree)
        reasoning = pick["reasoning"]
        prediction_code = pick["prediction"]
        confidence_pct = pick["confidence_pct"]
    else:
        # Sin mercado real, elegir el favorito del ML (argmax del blend),
        # no el "best EV" contra odds sintéticas que puede ser el outcome
        # menos probable.
        blend_outcome = max(blended, key=blended.get)
        prediction_code = {"home": "H", "draw": "D", "away": "A"}[blend_outcome]
        confidence_pct = blended[blend_outcome] * 100
        edge_pp = None
        ev_pct = None
        odds_display = None
        stake = 0.0
        tier = "free"
        prediction_label = {
            "H": f"{home_team} gana",
            "D": "Empate",
            "A": f"{away_team} gana",
        }[prediction_code]
        reasoning = (
            f"Predicción del modelo: {prediction_label} "
            f"({confidence_pct:.1f}% probabilidad). "
            "Sin línea de mercado verificada disponible — pick informativo, "
            "no recomendación de apuesta."
        )

    # Mercados secundarios via Poisson (OU 1.5/2.5/3.5 + DC 1X/X2/12).
    # Falla silenciosa si la forma no tiene goles — devuelve None y el pick
    # queda con `markets=None` (frontend ya maneja ausencia).
    poisson_markets: dict | None = None
    try:
        poisson_markets = build_market_outcomes(
            home_form=home_form,
            away_form=away_form,
            home_team=home_team,
            away_team=away_team,
            one_x_two_probs=blended,
        )
    except Exception as exc:
        print(f"[picks_service] poisson markets falló para {home_team}-{away_team}: {exc}")

    # Si hay cuotas reales en The Odds API, inyectamos odds + EV en cada outcome
    # OU/DC. Sin API key, esto es no-op y los outcomes quedan informativos.
    if poisson_markets and odds_is_configured():
        try:
            odds_entry = find_odds_for_match(home_team, away_team, slug)
            if odds_entry:
                poisson_markets = _apply_real_odds_to_markets(poisson_markets, odds_entry)
        except Exception as exc:
            print(f"[picks_service] aplicar odds reales falló para {home_team}-{away_team}: {exc}")

    result = {
        "id": str(uuid4()),
        "match": f"{home_team} vs {away_team}",
        "matchIcon": infer_match_icon(home_team, away_team),
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeLogo": _logo_url(home_team),
        "awayLogo": _logo_url(away_team),
        "league": cfg.name,
        "leagueLogo": cfg.logo,
        "leagueSlug": slug,
        "kickoff": "2026-04-19T16:30:00Z",
        "market": "ML",  # mercado del pick principal — siempre 1X2 hoy
        "prediction": PREDICTION_MAP.get(prediction_code, "home"),
        "confidence": int(round(confidence_pct)),
        "mlProb": {
            "home": round(ml_probs["home"], 4),
            "draw": round(ml_probs["draw"], 4),
            "away": round(ml_probs["away"], 4),
        },
        "polyProb": (
            {"home": round(poly_probs_dict["home"], 4),
             "draw": round(poly_probs_dict["draw"], 4),
             "away": round(poly_probs_dict["away"], 4)}
            if poly_probs_dict else None
        ),
        "bkProb": {
            "home": round(bk_probs["home"], 4),
            "draw": round(bk_probs["draw"], 4),
            "away": round(bk_probs["away"], 4),
        },
        "blendedProb": {
            "home": round(blended["home"], 4),
            "draw": round(blended["draw"], 4),
            "away": round(blended["away"], 4),
        },
        "aiReasoning": reasoning,
        "suggestedStake": stake,
        "status": tier,
        "odds": odds_display,
        "edgePp": edge_pp,
        "evPct": ev_pct,
        "sourcesAgree": sources_agree,
        "modelSource": ml_source,  # "ensemble" | "elo_fallback"
        "bookmakerSource": bookmaker_source,  # "bet365" | "synthetic"
        "marketVerified": market_verified,
        "polyMeta": poly_meta,
        "allOutcomes": pick["all_outcomes"],  # para parlay builder
        "markets": poisson_markets,           # OU + DC vía Poisson
    }

    # Claude narrativa solo si el pick tiene línea real y supera umbral (ahorra costo)
    if market_verified and pick.get("recommended"):
        try:
            narrative = generate_narrative(
                home=home_team,
                away=away_team,
                league=cfg.name,
                home_form=home_form,
                away_form=away_form,
                ml_probs=ml_probs,
                bookmaker_probs=bk_probs,
                polymarket_probs=poly_probs_dict,
                poly_liquidity=(poly_meta or {}).get("liquidity", 0.0),
                poly_volume_24h=(poly_meta or {}).get("volume_24h", 0.0),
            )
            result = merge_narrative_into_pick(result, narrative)
        except Exception as exc:
            print(f"[picks_service] claude narrative falló: {exc}")

    return result


def sync_fixtures_to_db(fixtures_list: list[dict], status: str = "scheduled") -> None:
    """
    Inserts or updates fixtures in the relational database.
    Each fixture is identified by its external_id: `league_slug:home_team:away_team:kickoff_iso`.
    """
    if not fixtures_list:
        return

    try:
        from datetime import datetime
        with connect() as cur:
            for f in fixtures_list:
                home = f.get("HomeTeam")
                away = f.get("AwayTeam")
                slug = f.get("leagueSlug")
                date_str = f.get("Date", "")
                time_str = f.get("Time", "")
                if not (home and away and slug):
                    continue

                match_dt = None
                if date_str:
                    try:
                        time_part = time_str if time_str else "00:00"
                        fmt = "%d/%m/%Y %H:%M" if len(date_str) > 8 else "%d/%m/%y %H:%M"
                        match_dt = datetime.strptime(f"{date_str} {time_part}", fmt)
                    except ValueError:
                        pass

                kickoff_iso = match_dt.isoformat() if match_dt else "2026-06-16T12:00:00"
                ext_id = f"{slug}:{home}:{away}:{kickoff_iso[:10]}"
                
                fthg = f.get("FTHG")
                ftag = f.get("FTAG")
                
                home_score = int(fthg) if fthg is not None and fthg != "" else None
                away_score = int(ftag) if ftag is not None and ftag != "" else None
                
                match_status = status
                if home_score is not None and away_score is not None:
                    match_status = "finished"

                cur.execute("SELECT id FROM fixtures WHERE external_id = %s", (ext_id,))
                row = cur.fetchone()
                if row:
                    fid = row["id"] if hasattr(row, "__getitem__") and "id" in row else row[0]
                    cur.execute(
                        """
                        UPDATE fixtures
                        SET status = %s, home_score = %s, away_score = %s, last_synced = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (match_status, home_score, away_score, fid),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO fixtures (external_id, league_slug, home_team, away_team, kickoff, status, home_score, away_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (ext_id, slug, home, away, kickoff_iso, match_status, home_score, away_score),
                    )
    except Exception as exc:
        print(f"[picks_service] Error syncing fixtures to DB: {exc}")


def save_picks_to_db(picks_list: list[dict]) -> None:
    """
    Saves or updates picks in the database.
    """
    if not picks_list:
        return

    try:
        import json
        with connect() as cur:
            for p in picks_list:
                ml = p["mlProb"]
                bk = p["bkProb"]
                poly = p.get("polyProb") or {}
                blended = p.get("blendedProb") or {}
                
                markets_json = json.dumps(p.get("markets")) if p.get("markets") else None
                poly_meta_json = json.dumps(p.get("polyMeta")) if p.get("polyMeta") else None
                
                cur.execute("SELECT id FROM picks WHERE id = %s", (p["id"],))
                if cur.fetchone():
                    cur.execute(
                        """
                        UPDATE picks
                        SET match = %s, home_team = %s, away_team = %s, home_logo = %s, away_logo = %s,
                            league = %s, league_logo = %s, league_slug = %s, market = %s, kickoff = %s,
                            prediction = %s, confidence = %s,
                            ml_prob_home = %s, ml_prob_draw = %s, ml_prob_away = %s,
                            poly_prob_home = %s, poly_prob_draw = %s, poly_prob_away = %s,
                            bk_prob_home = %s, bk_prob_draw = %s, bk_prob_away = %s,
                            blended_prob_home = %s, blended_prob_draw = %s, blended_prob_away = %s,
                            ai_reasoning = %s, suggested_stake = %s, status = %s, odds = %s,
                            edge_pp = %s, ev_pct = %s, sources_agree = %s, market_verified = %s,
                            markets_json = %s, poly_meta_json = %s
                        WHERE id = %s
                        """,
                        (
                            p["match"], p["homeTeam"], p["awayTeam"], p.get("homeLogo"), p.get("awayLogo"),
                            p["league"], p.get("leagueLogo"), p.get("leagueSlug"), p.get("market", "ML"), p["kickoff"],
                            p["prediction"], p["confidence"],
                            ml["home"], ml["draw"], ml["away"],
                            poly.get("home"), poly.get("draw"), poly.get("away"),
                            bk["home"], bk["draw"], bk["away"],
                            blended.get("home"), blended.get("draw"), blended.get("away"),
                            p["aiReasoning"], p["suggestedStake"], p["status"], p.get("odds"),
                            p.get("edgePp"), p.get("evPct"), p.get("sourcesAgree"), p.get("marketVerified"),
                            markets_json, poly_meta_json,
                            p["id"]
                        )
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO picks (
                            id, match, home_team, away_team, home_logo, away_logo,
                            league, league_logo, league_slug, market, kickoff, prediction, confidence,
                            ml_prob_home, ml_prob_draw, ml_prob_away,
                            poly_prob_home, poly_prob_draw, poly_prob_away,
                            bk_prob_home, bk_prob_draw, bk_prob_away,
                            blended_prob_home, blended_prob_draw, blended_prob_away,
                            ai_reasoning, suggested_stake, status, odds, edge_pp, ev_pct,
                            sources_agree, market_verified, markets_json, poly_meta_json
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        """,
                        (
                            p["id"], p["match"], p["homeTeam"], p["awayTeam"], p.get("homeLogo"), p.get("awayLogo"),
                            p["league"], p.get("leagueLogo"), p.get("leagueSlug"), p.get("market", "ML"), p["kickoff"],
                            p["prediction"], p["confidence"],
                            ml["home"], ml["draw"], ml["away"],
                            poly.get("home"), poly.get("draw"), poly.get("away"),
                            bk["home"], bk["draw"], bk["away"],
                            blended.get("home"), blended.get("draw"), blended.get("away"),
                            p["aiReasoning"], p["suggestedStake"], p["status"], p.get("odds"),
                            p.get("edgePp"), p.get("evPct"), p.get("sourcesAgree"), p.get("marketVerified"),
                            markets_json, poly_meta_json
                        )
                    )
    except Exception as exc:
        print(f"[picks_service] Error saving picks to DB: {exc}")


def load_picks_from_db(league_slug: str | None = None) -> list[dict]:
    """
    Loads upcoming picks from the database.
    """
    picks_list = []
    try:
        import json
        from datetime import datetime, timezone
        now_str = datetime.now(timezone.utc).isoformat()
        
        with connect() as cur:
            if league_slug:
                cur.execute(
                    "SELECT * FROM picks WHERE kickoff >= %s AND league_slug = %s ORDER BY kickoff ASC",
                    (now_str, league_slug)
                )
            else:
                cur.execute(
                    "SELECT * FROM picks WHERE kickoff >= %s ORDER BY kickoff ASC",
                    (now_str,)
                )
            
            rows = cur.fetchall()
            for r in rows:
                row_dict = {}
                if hasattr(r, "keys"):
                    row_dict = {k: r[k] for k in r.keys()}
                elif isinstance(r, dict):
                    row_dict = r
                else:
                    try:
                        row_dict = dict(r)
                    except Exception:
                        pass
                
                if not row_dict:
                    continue
                
                picks_list.append({
                    "id": row_dict["id"],
                    "match": row_dict["match"],
                    "homeTeam": row_dict["home_team"],
                    "awayTeam": row_dict["away_team"],
                    "homeLogo": row_dict.get("home_logo"),
                    "awayLogo": row_dict.get("away_logo"),
                    "league": row_dict["league"],
                    "leagueLogo": row_dict.get("league_logo"),
                    "leagueSlug": row_dict.get("league_slug"),
                    "market": row_dict.get("market") or "ML",
                    "kickoff": row_dict["kickoff"],
                    "prediction": row_dict["prediction"],
                    "confidence": row_dict["confidence"],
                    "mlProb": {
                        "home": row_dict["ml_prob_home"],
                        "draw": row_dict["ml_prob_draw"],
                        "away": row_dict["ml_prob_away"],
                    },
                    "polyProb": {
                        "home": row_dict["poly_prob_home"],
                        "draw": row_dict["poly_prob_draw"],
                        "away": row_dict["poly_prob_away"],
                    } if row_dict.get("poly_prob_home") is not None else None,
                    "bkProb": {
                        "home": row_dict["bk_prob_home"],
                        "draw": row_dict["bk_prob_draw"],
                        "away": row_dict["bk_prob_away"],
                    },
                    "blendedProb": {
                        "home": row_dict["blended_prob_home"],
                        "draw": row_dict["blended_prob_draw"],
                        "away": row_dict["blended_prob_away"],
                    } if row_dict.get("blended_prob_home") is not None else None,
                    "aiReasoning": row_dict.get("ai_reasoning") or "",
                    "suggestedStake": row_dict["suggested_stake"],
                    "status": row_dict["status"],
                    "odds": row_dict.get("odds"),
                    "edgePp": row_dict.get("edge_pp"),
                    "evPct": row_dict.get("ev_pct"),
                    "sourcesAgree": bool(row_dict["sources_agree"]) if row_dict.get("sources_agree") is not None else None,
                    "marketVerified": bool(row_dict["market_verified"]) if row_dict.get("market_verified") is not None else None,
                    "markets": json.loads(row_dict["markets_json"]) if row_dict.get("markets_json") else None,
                    "polyMeta": json.loads(row_dict["poly_meta_json"]) if row_dict.get("poly_meta_json") else None,
                })
    except Exception as exc:
        print(f"[picks_service] Error loading picks from DB: {exc}")
    
    return picks_list


def _kelly_fraction(prob: float | None, dec_odds: float | None, cap: float = 0.10) -> float:
    """Kelly fraccional acotado. f* = (b·p − q)/b, con b = odds−1, q = 1−p.
    Cap al 10% del bankroll para no recomendar stakes agresivos."""
    if prob is None or not dec_odds or dec_odds <= 1.0:
        return 0.0
    b = dec_odds - 1.0
    f = (b * prob - (1.0 - prob)) / b
    return round(max(0.0, min(f, cap)), 4)


def _lookup_fixture_id(cur, home: str | None, away: str | None, slug: str | None):
    """Best-effort: enlaza una predicción con su fixture persistido. None si no hay match."""
    try:
        if slug:
            cur.execute(
                "SELECT id FROM fixtures WHERE home_team=%s AND away_team=%s AND league_slug=%s "
                "ORDER BY id DESC LIMIT 1",
                (home, away, slug),
            )
        else:
            cur.execute(
                "SELECT id FROM fixtures WHERE home_team=%s AND away_team=%s ORDER BY id DESC LIMIT 1",
                (home, away),
            )
        row = cur.fetchone()
        if row:
            return row["id"] if hasattr(row, "keys") else row[0]
    except Exception:
        pass
    return None


def persist_predictions(picks_list: list[dict]) -> int:
    """Escribe la salida cruda del pipeline en la tabla `predictions` (registro
    ML/analítica, paralelo a `picks`). Idempotente por matchup: borra la fila
    previa del mismo home/away antes de insertar. Devuelve nº de filas escritas."""
    if not picks_list:
        return 0
    import os
    method = os.environ.get("PREDICTION_METHOD", "ensemble")
    written = 0
    try:
        with connect() as cur:
            for p in picks_list:
                blended = p.get("blendedProb") or p.get("mlProb") or {}
                bk = p.get("bkProb") or {}
                ph, pdraw, pa = blended.get("home"), blended.get("draw"), blended.get("away")
                rec = p.get("prediction")

                def _imp_odds(side: str) -> float | None:
                    ip = bk.get(side)
                    return (1.0 / ip) if ip and ip > 0 else None

                def _ev(prob: float | None, side: str) -> float | None:
                    # Para el lado recomendado usamos la línea real (p["odds"]) si existe;
                    # para los demás, derivamos de la prob implícita del bookmaker.
                    o = p.get("odds") if side == rec and p.get("odds") else _imp_odds(side)
                    return round(prob * o - 1.0, 4) if (prob is not None and o) else None

                rec_prob = blended.get(rec) if rec in ("home", "draw", "away") else None
                rec_odds = p.get("odds") or (_imp_odds(rec) if rec in ("home", "draw", "away") else None)
                kelly = _kelly_fraction(rec_prob, rec_odds)

                kickoff = p.get("kickoff")
                match_date = kickoff[:10] if isinstance(kickoff, str) and len(kickoff) >= 10 else None
                home, away = p.get("homeTeam"), p.get("awayTeam")
                fixture_id = _lookup_fixture_id(cur, home, away, p.get("leagueSlug"))

                # Idempotencia: una predicción vigente por matchup.
                cur.execute(
                    "DELETE FROM predictions WHERE home_team=%s AND away_team=%s",
                    (home, away),
                )
                cur.execute(
                    """
                    INSERT INTO predictions (
                        fixture_id, match_date, league, home_team, away_team,
                        predicted_prob_home, predicted_prob_draw, predicted_prob_away,
                        ev_home, ev_draw, ev_away, recommended_bet, kelly_stake,
                        narrative, method, expires_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        fixture_id, match_date, p.get("league"), home, away,
                        ph, pdraw, pa,
                        _ev(ph, "home"), _ev(pdraw, "draw"), _ev(pa, "away"),
                        rec, kelly, p.get("aiReasoning"), method, kickoff,
                    ),
                )
                written += 1
    except Exception as exc:
        print(f"[picks_service] Error persisting predictions: {exc}")
    return written


def generate_and_persist_picks(date: str | None = None, league_slug: str | None = None) -> list[dict]:
    """Corre el pipeline completo (ML + Polymarket + Bet365 + narrativa Claude) y
    persiste los resultados en `picks` (formato frontend) y `predictions`
    (registro ML). Es el único punto que computa picks; los endpoints solo leen.

    `date` se acepta por compatibilidad con el contrato del overhaul; el pool se
    genera para todos los fixtures próximos (que es lo que consume el dashboard).
    """
    picks_list = _compute_picks(league_slug=league_slug)
    if picks_list:
        save_picks_to_db(picks_list)
        persist_predictions(picks_list)
    return picks_list


def read_picks_from_db(date: str | None = None, league_slug: str | None = None) -> list[dict]:
    """Lee picks persistidos (tabla `picks`, formato frontend). Solo lectura: no
    dispara cómputo. Por defecto devuelve los próximos (kickoff >= ahora), que es
    lo que el dashboard pide para "hoy". `date` reservado para filtros futuros."""
    return load_picks_from_db(league_slug)


def precompute_and_save_picks() -> None:
    """Wrapper retro-compatible para el scheduler — delega en el pipeline unificado."""
    print("[scheduler] Iniciando precomputo de picks...")
    try:
        picks_list = generate_and_persist_picks()
        if picks_list:
            print(f"[scheduler] ✓ Generados y persistidos {len(picks_list)} picks (picks + predictions).")
        else:
            print("[scheduler] No se generaron picks para guardar.")
    except Exception as e:
        print(f"[scheduler] Error precomputando picks: {e}")


def get_todays_picks(league_slug: str | None = None) -> list[dict]:
    """Devuelve el pool de picks de hoy. Lectura de DB únicamente; si la tabla
    está vacía, dispara generación una sola vez de forma síncrona y relee.
    Sin cache en memoria — la persistencia en DB es la fuente de verdad."""
    picks = read_picks_from_db(league_slug=league_slug)
    if picks:
        return picks
    generate_and_persist_picks(league_slug=league_slug)
    return read_picks_from_db(league_slug=league_slug)


def _compute_picks(league_slug: str | None = None) -> list[dict]:
    slugs = [league_slug] if league_slug and league_slug in LEAGUES else list(LEAGUES.keys())
    picks: list[dict] = []

    # Fixtures reales vía openfootball (solo las 5 grandes; CL y WC no están en ese feed)
    domestic_slugs = [s for s in slugs if s not in ("champions-league", "fifa-world-cup")]
    fixtures = load_fixtures_of(domestic_slugs) if domestic_slugs else []

    # Sincronizar fixtures programados en DB
    if fixtures:
        sync_fixtures_to_db(fixtures, status="scheduled")

    # Sincronizar resultados históricos recientes (últimos 14 días) para settlement
    for slug in domestic_slugs:
        try:
            history = load_history_of(slug)
            if history:
                from datetime import datetime, timedelta
                cutoff = datetime.utcnow() - timedelta(days=14)
                recent = [m for m in history if m.get("DateObj") and m["DateObj"] >= cutoff]
                for r in recent:
                    r["leagueSlug"] = slug
                sync_fixtures_to_db(recent, status="finished")
        except Exception as e:
            print(f"[picks_service] Error syncing history for {slug}: {e}")

    now_utc = datetime.now(timezone.utc)

    for i, slug in enumerate(slugs):
        matchups: list[tuple[str, str, str, str, dict | None]] = []
        if slug == "champions-league":
            try:
                cl_to_sync = []
                for cl in list_cl_fixtures():
                    matchups.append((cl.home, cl.away, cl.date, cl.time, None))
                    cl_to_sync.append({
                        "HomeTeam": cl.home,
                        "AwayTeam": cl.away,
                        "Date": cl.date,
                        "Time": cl.time,
                        "leagueSlug": slug
                    })
                if cl_to_sync:
                    sync_fixtures_to_db(cl_to_sync, status="scheduled")
            except Exception as e:
                print(f"[picks_service] Error cargando fixtures de CL: {e}")
        elif slug == "fifa-world-cup":
            try:
                from data.team_name_map import canonicalize
                wc_to_sync = []
                api_fixtures = []
                if odds_is_configured():
                    try:
                        api_fixtures = fetch_league_odds(slug)
                    except Exception as e:
                        print(f"[picks_service] Error al obtener odds de WC desde API: {e}")

                if api_fixtures:
                    print(f"[picks_service] Obtenidos {len(api_fixtures)} fixtures reales del Mundial desde la API.")
                    for entry in api_fixtures:
                        ko = entry.get("kickoff", "")
                        try:
                            dt = datetime.fromisoformat(ko.replace("Z", "+00:00"))
                        except ValueError:
                            continue
                        
                        # Canonicalizar nombres de equipos para ELO y Predictor
                        home_canon = canonicalize(entry["home_team"])
                        away_canon = canonicalize(entry["away_team"])
                        
                        matchups.append((home_canon, away_canon, dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M"), None))
                        wc_to_sync.append({
                            "HomeTeam": home_canon,
                            "AwayTeam": away_canon,
                            "Date": dt.strftime("%d/%m/%Y"),
                            "Time": dt.strftime("%H:%M"),
                            "leagueSlug": slug
                        })
                else:
                    # Fallback a los fixtures curados tradicionales si la API no está configurada o falló
                    print("[picks_service] Fallback a fixtures curados para fifa-world-cup")
                    for wc in list_wc_fixtures():
                        matchups.append((wc.home, wc.away, wc.date, wc.time, None))
                        wc_to_sync.append({
                            "HomeTeam": wc.home,
                            "AwayTeam": wc.away,
                            "Date": wc.date,
                            "Time": wc.time,
                            "leagueSlug": slug
                        })
                
                if wc_to_sync:
                    sync_fixtures_to_db(wc_to_sync, status="scheduled")
            except Exception as e:
                print(f"[picks_service] Error cargando fixtures de WC: {e}")
        else:
            league_fixtures = [f for f in fixtures if f.get("leagueSlug") == slug]
            # Limitamos a próximos 7 días para mantener el pool relevante
            for row in league_fixtures[:20]:
                matchups.append((
                    row["HomeTeam"], row["AwayTeam"],
                    row.get("Date", ""), row.get("Time", ""),
                    row,
                ))
            # Fallback: si openfootball no tiene fixtures (p.ej. Liga MX 2025-26
            # aún no publicado), usamos The Odds API events. Cada entry viene
            # con cuotas reales adjuntas — el pick principal y los markets
            # secundarios se benefician automáticamente.
            #
            # IMPORTANTE: si NINGUNA fuente tiene fixtures reales, devolvemos
            # lista vacía. JAMÁS generamos matchups sintéticos a partir de
            # `LEAGUES[slug].featured` — eso era ficción y rompe la confianza
            # en la app.
            if not matchups and odds_is_configured():
                try:
                    for entry in fetch_league_odds(slug)[:10]:
                        ko = entry.get("kickoff", "")
                        try:
                            dt = datetime.fromisoformat(ko.replace("Z", "+00:00"))
                        except ValueError:
                            continue
                        matchups.append((
                            entry["home_team"], entry["away_team"],
                            dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M"),
                            None,
                        ))
                except Exception as exc:
                    print(f"[picks_service] odds API fixtures fallback falló para {slug}: {exc}")

        for j, match_info in enumerate(matchups):
            home, away, date_str, time_str, row = match_info

            match_dt = None
            if date_str and time_str:
                try:
                    fmt = "%d/%m/%Y %H:%M" if len(date_str) > 8 else "%d/%m/%y %H:%M"
                    dt = datetime.strptime(f"{date_str} {time_str}", fmt)
                    match_dt = dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            if match_dt and match_dt < now_utc:
                continue

            seed = i * 100 + j
            pick = _build_pick_for_match(slug, home, away, seed=seed, fixture_row=row)
            if pick:
                if match_dt:
                    pick["kickoff"] = match_dt.isoformat()
                picks.append(pick)

    # Orden: primero picks con línea real (por EV desc), luego el resto (por confianza desc).
    # Así los picks "market-verified" suben arriba y las predicciones informativas quedan abajo.
    def _sort_key(p: dict) -> tuple:
        verified = 1 if p.get("marketVerified") else 0
        ev = p.get("evPct") if p.get("evPct") is not None else -999
        conf = p.get("confidence", 0)
        return (verified, ev, conf)

    picks.sort(key=_sort_key, reverse=True)
    return picks


def get_leagues() -> list[dict]:
    return [
        {"slug": cfg.slug, "name": cfg.name, "code": cfg.fd_code, "logo": cfg.logo}
        for cfg in LEAGUES.values()
    ]
