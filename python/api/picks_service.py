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
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
from deterministic_pick import generate_pick

# TTL en segundos para el pool completo de picks. Los picks solo cambian
# cuando cambia la lista de fixtures o el modelo — 5 min es razonable.
_PICKS_TTL_SECONDS = 300
_picks_cache: dict[str, tuple[float, list[dict]]] = {}

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

    # ML probs (ensemble o ELO fallback)
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


def get_todays_picks(league_slug: str | None = None) -> list[dict]:
    cache_key = league_slug or "__all__"
    now = time.time()
    cached = _picks_cache.get(cache_key)
    if cached and (now - cached[0]) < _PICKS_TTL_SECONDS:
        return cached[1]

    result = _compute_picks(league_slug)
    # Cache con TTL largo si hay resultados; corto si está vacío (red caída o sin
    # fixtures hoy) para no hammerear la red pero permitir recuperación rápida.
    ttl_entry = (now, result) if result else (now - _PICKS_TTL_SECONDS + 30, result)
    _picks_cache[cache_key] = ttl_entry
    return result


def _compute_picks(league_slug: str | None = None) -> list[dict]:
    slugs = [league_slug] if league_slug and league_slug in LEAGUES else list(LEAGUES.keys())
    picks: list[dict] = []

    # Fixtures reales vía openfootball (solo las 5 grandes; CL no está en ese feed)
    domestic_slugs = [s for s in slugs if s != "champions-league"]
    fixtures = load_fixtures_of(domestic_slugs) if domestic_slugs else []

    now_utc = datetime.now(timezone.utc)

    for i, slug in enumerate(slugs):
        matchups: list[tuple[str, str, str, str, dict | None]] = []
        if slug == "champions-league":
            try:
                for cl in list_cl_fixtures():
                    matchups.append((cl.home, cl.away, cl.date, cl.time, None))
            except Exception as e:
                print(f"[picks_service] Error cargando fixtures de CL: {e}")
        else:
            league_fixtures = [f for f in fixtures if f.get("leagueSlug") == slug]
            # Limitamos a próximos 7 días para mantener el pool relevante
            for row in league_fixtures[:20]:
                matchups.append((
                    row["HomeTeam"], row["AwayTeam"],
                    row.get("Date", ""), row.get("Time", ""),
                    row,
                ))
            # Fallback 1: si openfootball no tiene fixtures (p.ej. Liga MX 2025-26
            # aún no publicado), usamos The Odds API events que ya viene con
            # cuotas reales adjuntas — pick principal se beneficia automáticamente.
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

            # Fallback 2: matchups `featured` de la config — último recurso si
            # ni openfootball ni The Odds API tienen fixtures para esta liga.
            if not matchups and LEAGUES[slug].featured:
                synth_dt = now_utc + timedelta(days=7)
                for fh, fa in LEAGUES[slug].featured:
                    matchups.append((
                        fh, fa,
                        synth_dt.strftime("%d/%m/%Y"),
                        synth_dt.strftime("%H:%M"),
                        None,
                    ))

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
