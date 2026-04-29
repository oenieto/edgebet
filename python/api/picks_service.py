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
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

# TTL en segundos para el pool completo de picks. Los picks solo cambian
# cuando cambia la lista de fixtures o el modelo — 5 min es razonable.
_PICKS_TTL_SECONDS = 300
_picks_cache: dict[str, tuple[float, list[dict]]] = {}

# Permitir imports desde python/
_PY_ROOT = Path(__file__).resolve().parent.parent
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

PREDICTION_MAP = {"H": "home", "D": "draw", "A": "away"}


@dataclass
class LeagueConfig:
    slug: str
    name: str
    fd_code: str
    seasons: tuple[str, ...]
    featured: tuple[tuple[str, str], ...]


LEAGUES: dict[str, LeagueConfig] = {
    "premier-league": LeagueConfig(
        slug="premier-league",
        name="Premier League",
        fd_code="E0",
        seasons=("2425", "2324"),
        featured=(("Man City", "Arsenal"), ("Liverpool", "Chelsea")),
    ),
    "la-liga": LeagueConfig(
        slug="la-liga",
        name="La Liga",
        fd_code="SP1",
        seasons=("2425", "2324"),
        featured=(("Real Madrid", "Barcelona"), ("Atletico Madrid", "Sevilla")),
    ),
    "bundesliga": LeagueConfig(
        slug="bundesliga",
        name="Bundesliga",
        fd_code="D1",
        seasons=("2425", "2324"),
        featured=(("Bayern Munich", "Dortmund"), ("Leverkusen", "RB Leipzig")),
    ),
    "serie-a": LeagueConfig(
        slug="serie-a",
        name="Serie A",
        fd_code="I1",
        seasons=("2425", "2324"),
        featured=(("Inter", "Juventus"), ("Napoli", "Milan")),
    ),
    "ligue-1": LeagueConfig(
        slug="ligue-1",
        name="Ligue 1",
        fd_code="F1",
        seasons=("2425", "2324"),
        featured=(("Paris SG", "Marseille"), ("Monaco", "Lille")),
    ),
    "champions-league": LeagueConfig(
        slug="champions-league",
        name="UEFA Champions League",
        fd_code="UCL",  # marcador — no se baja de football-data.co.uk
        seasons=(),     # sin histórico propio; se cruzan las 5 ligas top
        featured=(),
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
            from api.db import connect
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
    from api.fast_loader import compute_elo
    from api.openfootball_loader import load_history_of
    cfg = LEAGUES[slug]
    if slug == "champions-league":
        from api.champions_league import load_cl_context
        matches, ratings = load_cl_context()
        return matches, ratings, cfg
    # openfootball como fuente primaria (GitHub, siempre reachable)
    matches = load_history_of(slug)
    ratings = compute_elo(matches, k=32, home_advantage=65)
    return matches, ratings, cfg


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

    from api.fast_loader import compute_team_form
    from api import predictor
    from api.claude_narrative import generate_narrative, merge_narrative_into_pick

    home_form = compute_team_form(matches, home_team)
    away_form = compute_team_form(matches, away_team)

    # Bookmaker: reales si vienen en el fixture; si no, sintéticas
    bookmaker: tuple[dict, dict] | None = None
    if fixture_row:
        bookmaker = _real_bookmaker_from_fixture(fixture_row)

    elo_probs_preview = predictor.baseline_elo_probs(
        ratings.get(home_team, 1500.0), ratings.get(away_team, 1500.0)
    )
    if bookmaker is None:
        bk_probs, bk_odds = _synth_bookmaker_odds(elo_probs_preview, seed=seed)
        bookmaker_source = "synthetic"
    else:
        bk_probs, bk_odds = bookmaker
        bookmaker_source = "bet365"

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
        from api.polymarket_live import find_match_probs
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
    from deterministic_pick import generate_pick
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
    market_verified = bookmaker_source == "bet365"
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

    result = {
        "id": str(uuid4()),
        "match": f"{home_team} vs {away_team}",
        "matchIcon": infer_match_icon(home_team, away_team),
        "homeTeam": home_team,
        "awayTeam": away_team,
        "league": cfg.name,
        "leagueSlug": slug,
        "kickoff": "2026-04-19T16:30:00Z",
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
    from api.openfootball_loader import load_fixtures_of

    slugs = [league_slug] if league_slug and league_slug in LEAGUES else list(LEAGUES.keys())
    picks: list[dict] = []

    # Fixtures reales vía openfootball (solo las 5 grandes; CL no está en ese feed)
    domestic_slugs = [s for s in slugs if s != "champions-league"]
    fixtures = load_fixtures_of(domestic_slugs) if domestic_slugs else []

    now_utc = datetime.now(timezone.utc)

    for i, slug in enumerate(slugs):
        matchups: list[tuple[str, str, str, str, dict | None]] = []
        if slug == "champions-league":
            # CL solo se activa si tenemos fuente verificada (API key externa).
            # No inventamos fixtures — si no hay feed, se omite la liga.
            from api.champions_league import list_fixtures
            for cl in list_fixtures():
                matchups.append((cl.home, cl.away, cl.date, cl.time, None))
        else:
            league_fixtures = [f for f in fixtures if f.get("leagueSlug") == slug]
            # Limitamos a próximos 7 días para mantener el pool relevante
            for row in league_fixtures[:20]:
                matchups.append((
                    row["HomeTeam"], row["AwayTeam"],
                    row.get("Date", ""), row.get("Time", ""),
                    row,
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
        {"slug": cfg.slug, "name": cfg.name, "code": cfg.fd_code}
        for cfg in LEAGUES.values()
    ]
