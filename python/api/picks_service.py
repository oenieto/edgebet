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

import json
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import hashlib
import uuid

try:
    import redis
    REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

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
) -> list[dict]:
    try:
        matches, ratings, cfg = _load_league(slug)
    except Exception as exc:
        print(f"[picks_service] no pude cargar liga {slug}: {exc}")
        return []

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
    
    is_big_match = (ratings.get(home_team, 1500.0) > 1800.0 or ratings.get(away_team, 1500.0) > 1800.0) or slug == "champions-league"

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
        if tier == "free" and is_big_match:
            tier = "premium"
        reasoning = pick["reasoning"]
        prediction_code = pick["prediction"]
        confidence_pct = pick["confidence_pct"]
    else:
        # Sin mercado real, elegir el favorito del ML (argmax del blend),
        # no el "best EV" contra odds sintéticas que puede ser el outcome
        # menos probable.
        # Anti-draw bias: el ensemble entrenado en CSVs con stats granulares
        # (shots/SoT/corners) recibe esos features como constantes de liga
        # cuando la fuente live es openfootball — sin diferenciación, predice
        # empate por defecto. Cuando los equipos están bien diferenciados por
        # ELO/forma, el empate rara vez es la lectura correcta del mercado.
        #
        # Regla:
        #   1) Si home y away están muy parejos (gap <4pp) Y el draw es claro
        #      ganador (>5pp sobre cada uno), aceptamos el empate.
        #   2) En cualquier otro caso, elegimos entre home/away por forma+ELO,
        #      ignorando la masa de probabilidad asignada al empate.
        h_p, d_p, a_p = blended["home"], blended["draw"], blended["away"]
        elo_gap = ratings.get(home_team, 1500.0) - ratings.get(away_team, 1500.0)
        form_gap = float(home_form.get("Form", 1.3)) - float(away_form.get("Form", 1.2))
        teams_balanced = abs(h_p - a_p) < 0.04 and abs(elo_gap) < 80
        draw_clearly_best = d_p > h_p + 0.05 and d_p > a_p + 0.05

        if teams_balanced and draw_clearly_best:
            blend_outcome = "draw"
        else:
            # Reasignar la masa de empate proporcionalmente a home/away,
            # luego elegir el favorito. Mezcla con form+ELO para romper empates.
            redistributed_home = h_p + d_p * (h_p / max(h_p + a_p, 0.01))
            redistributed_away = a_p + d_p * (a_p / max(h_p + a_p, 0.01))
            tilt = 0.02 * (1 if elo_gap + form_gap * 50 > 0 else -1)
            if redistributed_home + tilt >= redistributed_away:
                blend_outcome = "home"
            else:
                blend_outcome = "away"

        prediction_code = {"home": "H", "draw": "D", "away": "A"}[blend_outcome]
        confidence_pct = blended[blend_outcome] * 100
        
        synthetic_odds_ml = round((1.0 / blended[blend_outcome]) * 1.08, 2)
        ev_val_ml = (blended[blend_outcome] * synthetic_odds_ml) - 1.0
        edge_val_ml = blended[blend_outcome] - (1.0 / synthetic_odds_ml)
        
        edge_pp = round(edge_val_ml * 100, 1)
        ev_pct = round(ev_val_ml * 100, 1)
        odds_display = synthetic_odds_ml
        stake = round(ev_val_ml * 10, 2) if ev_val_ml > 0 else 1.0
        
        if edge_val_ml > 0.08:
            tier = "vip"
        else:
            tier = "premium" if is_big_match else "free"
            
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

    from api.team_logos import logo_url
    result = {
        "id": str(uuid.UUID(hashlib.md5(f"{home_team}-{away_team}-ML".encode()).hexdigest())),
        "match": f"{home_team} vs {away_team}",
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeLogo": logo_url(home_team),
        "awayLogo": logo_url(away_team),
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

    result["market"] = "ML"
    out_picks = [result]

    # Generación del Pick Over/Under usando métricas ofensivas/defensivas (Poisson)
    home_gf = float(home_form.get("avg_GF", 1.2))
    home_ga = float(home_form.get("avg_GA", 1.2))
    away_gf = float(away_form.get("avg_GF", 1.1))
    away_ga = float(away_form.get("avg_GA", 1.3))
    
    exp_total = (home_gf + away_ga + away_gf + home_ga) / 2
    
    import math
    def poisson_pmf(k, lam):
        return (lam ** k * math.exp(-lam)) / math.factorial(k)
        
    p0 = poisson_pmf(0, exp_total)
    p1 = poisson_pmf(1, exp_total)
    p2 = poisson_pmf(2, exp_total)
    p3 = poisson_pmf(3, exp_total)
    
    u15 = p0 + p1
    o15 = 1 - u15
    u25 = u15 + p2
    o25 = 1 - u25
    u35 = u25 + p3
    o35 = 1 - u35
    
    if exp_total >= 3.3:
        target_line = "3_5"
        prob_over, prob_under = o35, u35
        ai_msg = f"Equipos con esquemas ultraofensivos y problemas defensivos ({exp_total:.1f} goles esperados). El Over 3.5 ofrece un ratio riesgo/beneficio excelente."
    elif exp_total >= 2.6:
        target_line = "2_5"
        prob_over, prob_under = o25, u25
        ai_msg = f"Tendencia a partidos abiertos ({exp_total:.1f} goles esperados). Over 2.5 es la línea más segura."
    elif exp_total <= 1.8:
        target_line = "1_5"
        prob_over, prob_under = o15, u15
        ai_msg = f"Defensas férreas y muy bajo goleo proyectado ({exp_total:.1f}). Under 1.5 es arriesgado pero ofrece gran valor estadístico."
    elif exp_total <= 2.3:
        target_line = "2_5"
        prob_over, prob_under = o25, u25
        ai_msg = f"Partido que se proyecta cerrado y táctico ({exp_total:.1f} goles esperados). Under 2.5 tiene un alto margen de seguridad."
    else:
        target_line = "2_5"
        prob_over, prob_under = o25, u25
        ai_msg = f"Promedio de goleo equilibrado ({exp_total:.1f} goles esperados). Recomendamos la línea estándar de 2.5."
    
    ou_pred_code = f"over_{target_line}" if prob_over > prob_under else f"under_{target_line}"
    ou_conf = max(prob_over, prob_under) * 100
    
    fair_prob = max(prob_over, prob_under)
    synthetic_odds = round((1.0 / fair_prob) * 1.12, 2) 
    ev_val = (fair_prob * synthetic_odds) - 1.0
    edge_val = fair_prob - (1.0 / synthetic_odds)

    ou_result = {
        "id": str(uuid.UUID(hashlib.md5(f"{home_team}-{away_team}-OU".encode()).hexdigest())),
        "market": "OU",
        "match": f"{home_team} vs {away_team}",
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeLogo": logo_url(home_team),
        "awayLogo": logo_url(away_team),
        "league": cfg.name,
        "leagueSlug": slug,
        "kickoff": "2026-04-19T16:30:00Z",
        "prediction": ou_pred_code,
        "confidence": int(round(ou_conf)),
        "mlProb": {f"over_{target_line}": round(prob_over, 4), f"under_{target_line}": round(prob_under, 4)},
        "polyProb": None,
        "bkProb": {f"over_{target_line}": round(prob_over, 4), f"under_{target_line}": round(prob_under, 4)},
        "blendedProb": {f"over_{target_line}": round(prob_over, 4), f"under_{target_line}": round(prob_under, 4)},
        "aiReasoning": ai_msg,
        "suggestedStake": round(ev_val * 10, 2) if ev_val > 0 else 1.5,
        "status": "vip" if edge_val > 0.08 else ("premium" if is_big_match else "free"),
        "odds": synthetic_odds,
        "edgePp": round(edge_val * 100, 1),
        "evPct": round(ev_val * 100, 1),
        "sourcesAgree": True,
        "modelSource": "poisson_dynamic",
        "bookmakerSource": "synthetic",
        "marketVerified": False,
        "polyMeta": None,
        "allOutcomes": []
    }
    
    out_picks.append(ou_result)

    # DOBLE OPORTUNIDAD (Double Chance)
    dc_1x = blended["home"] + blended["draw"]
    dc_x2 = blended["draw"] + blended["away"]
    dc_12 = blended["home"] + blended["away"]
    
    dc_probs = {"1X": dc_1x, "X2": dc_x2, "12": dc_12}
    best_dc = max(dc_probs, key=dc_probs.get)
    best_dc_prob = dc_probs[best_dc]
    dc_odds = round((1.0 / best_dc_prob) * 1.08, 2)
    
    dc_result = {
        "id": str(uuid.UUID(hashlib.md5(f"{home_team}-{away_team}-DC".encode()).hexdigest())),
        "market": "DC",
        "match": f"{home_team} vs {away_team}",
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeLogo": logo_url(home_team),
        "awayLogo": logo_url(away_team),
        "league": cfg.name,
        "leagueSlug": slug,
        "kickoff": "2026-04-19T16:30:00Z",
        "prediction": best_dc,
        "confidence": int(round(best_dc_prob * 100)),
        "mlProb": {k: round(v, 4) for k, v in dc_probs.items()},
        "polyProb": None,
        "bkProb": {k: round(v, 4) for k, v in dc_probs.items()},
        "blendedProb": {k: round(v, 4) for k, v in dc_probs.items()},
        "aiReasoning": f"Modo Seguro: Doble oportunidad {best_dc} respaldado por sólida probabilidad de {best_dc_prob*100:.1f}%. Ideal para construir bankroll.",
        "suggestedStake": 2.5,
        "status": "premium" if is_big_match else "free",
        "odds": dc_odds,
        "edgePp": 0.0,
        "evPct": 0.0,
        "sourcesAgree": True,
        "modelSource": "poisson_dynamic",
        "bookmakerSource": "synthetic",
        "marketVerified": False,
        "polyMeta": None,
        "allOutcomes": [],
    }
    out_picks.append(dc_result)

    # Generar Combos (Ambos Anotan + ML + OU)
    # Probabilidad Ambos Anotan (AA / BTTS) usando Poisson
    # P(Ambos Anotan) = P(Home > 0) * P(Away > 0)
    p_home_scores = 1 - poisson_pmf(0, home_gf + away_ga)
    p_away_scores = 1 - poisson_pmf(0, away_gf + home_ga)
    p_btts = p_home_scores * p_away_scores
    
    btts_label = "AA" if p_btts >= 0.55 else "No AA"
    
    fav_ml = max(blended, key=blended.get)
    fav_team = home_team if fav_ml == "home" else away_team if fav_ml == "away" else "Empate"
    
    combos = {
        "safe": btts_label,
        "medium": f"{btts_label} y {ou_pred_code.replace('_', ' ').replace('over', 'Más de').replace('under', 'Menos de')}",
        "risky": f"{fav_team} gana y {btts_label}"
    }
    
    # Asignar combos a todos los picks generados para este partido
    for pick in out_picks:
        pick["combos"] = combos

    return out_picks


def get_todays_picks(league_slug: str | None = None) -> list[dict]:
    cache_key = f"picks:{league_slug or '__all__'}"
    now = time.time()
    
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"[picks_service] redis read error: {e}")
    else:
        cached_mem = _picks_cache.get(cache_key)
        if cached_mem and (now - cached_mem[0]) < _PICKS_TTL_SECONDS:
            return cached_mem[1]

    result = _compute_picks(league_slug)
    
    if redis_client:
        try:
            ttl = _PICKS_TTL_SECONDS if result else 30
            redis_client.setex(cache_key, ttl, json.dumps(result))
        except Exception as e:
            print(f"[picks_service] redis write error: {e}")
    else:
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
            # Ampliamos a próximos 14 días (aprox 40 partidos por liga) para mantener el pool relevante
            for row in league_fixtures[:40]:
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
            match_picks = _build_pick_for_match(slug, home, away, seed=seed, fixture_row=row)
            for p in match_picks:
                if match_dt:
                    p["kickoff"] = match_dt.isoformat()
                picks.append(p)

    # Orden: primero picks con línea real (por EV desc), luego el resto (por confianza desc).
    # Así los picks "market-verified" suben arriba y las predicciones informativas quedan abajo.
    def _sort_key(p: dict) -> tuple:
        verified = 1 if p.get("marketVerified") else 0
        ev = p.get("evPct") if p.get("evPct") is not None else -999
        conf = p.get("confidence", 0)
        return (verified, ev, conf)

    picks.sort(key=_sort_key, reverse=True)

    # Agrupar por partido y emitir TODOS los mercados disponibles.
    # Se ordenan: ML primero (resultado), luego OU (goles), luego DC (doble oportunidad).
    # Cada pick lleva un campo "market" para que el frontend lo filtre si quiere.
    MARKET_ORDER = {"ML": 0, "OU": 1, "DC": 2}
    by_match: dict[str, list[dict]] = {}
    for p in picks:
        key = p["match"]
        by_match.setdefault(key, []).append(p)

    chosen: list[dict] = []
    for match, options in by_match.items():
        # Ordenar mercados dentro del partido
        options_sorted = sorted(options, key=lambda o: MARKET_ORDER.get(o.get("market", ""), 99))
        chosen.extend(options_sorted)

    chosen.sort(key=lambda p: (
        p.get("kickoff", ""),
        MARKET_ORDER.get(p.get("market", ""), 99),
    ))
    return chosen


def get_leagues() -> list[dict]:
    return [
        {"slug": cfg.slug, "name": cfg.name, "code": cfg.fd_code}
        for cfg in LEAGUES.values()
    ]


def get_pick_stats(pick_id: str) -> dict | None:
    from api.team_logos import logo_url

    picks = get_todays_picks()
    pick = next((p for p in picks if p["id"] == pick_id), None)
    if not pick:
        return None

    slug = pick.get("leagueSlug")
    home = pick.get("homeTeam")
    away = pick.get("awayTeam")
    if not slug or not home or not away:
        return None

    try:
        matches, ratings, cfg = _load_league(slug)
    except Exception:
        return None

    # Para CL: cruzar también con los datasets domésticos para el H2H,
    # ya que el contexto unificado ya incluye las 5 grandes ligas.
    def _format_match(m, target_team: str | None = None):
        fthg = m.get("FTHG")
        ftag = m.get("FTAG")
        score = f"{fthg}-{ftag}" if fthg is not None and ftag is not None else "vs"
        match_home = m.get("HomeTeam", "")
        match_away = m.get("AwayTeam", "")

        # Resultado relativo a target_team (W/L/D)
        result = None
        if target_team and fthg is not None and ftag is not None:
            is_home = match_home == target_team
            if fthg == ftag:
                result = "D"
            elif (fthg > ftag and is_home) or (ftag > fthg and not is_home):
                result = "W"
            else:
                result = "L"

        return {
            "date": m.get("Date", ""),
            "home": match_home,
            "away": match_away,
            "homeLogo": logo_url(match_home),
            "awayLogo": logo_url(match_away),
            "score": score,
            "result": result,
        }

    h2h = [
        m for m in matches
        if (m.get("HomeTeam") == home and m.get("AwayTeam") == away)
        or (m.get("HomeTeam") == away and m.get("AwayTeam") == home)
    ]
    # Solo partidos jugados (con score), ordenados del más reciente al más antiguo
    h2h = [m for m in h2h if m.get("FTHG") is not None]
    h2h.sort(key=lambda m: m.get("DateObj"), reverse=True)

    def _team_last_played(team: str, n: int = 5) -> list[dict]:
        team_matches = [
            m for m in matches
            if (m.get("HomeTeam") == team or m.get("AwayTeam") == team)
            and m.get("FTHG") is not None
        ]
        team_matches.sort(key=lambda m: m.get("DateObj"), reverse=True)
        return [_format_match(m, target_team=team) for m in team_matches[:n]]

    # Form W/D/L compacta (string tipo "WWDLW") — útil para badges en UI
    def _form_string(team_last: list[dict]) -> str:
        # Mostrarlo cronológico (antiguo→nuevo) para leerse natural
        return "".join(item["result"] or "?" for item in reversed(team_last))

    # Métricas agregadas por equipo en sus últimos N
    def _aggregate(team_last: list[dict], team: str) -> dict:
        wins = draws = losses = 0
        gf = ga = 0
        for item in team_last:
            r = item["result"]
            if r == "W":
                wins += 1
            elif r == "D":
                draws += 1
            elif r == "L":
                losses += 1
            try:
                h, a = item["score"].split("-")
                h, a = int(h), int(a)
                if item["home"] == team:
                    gf += h; ga += a
                else:
                    gf += a; ga += h
            except (ValueError, AttributeError):
                pass
        return {
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
        }

    home_last_5 = _team_last_played(home, 5)
    away_last_5 = _team_last_played(away, 5)

    return {
        "h2h": [_format_match(m, target_team=home) for m in h2h[:5]],
        "home_stats": {
            "team": home,
            "logo": logo_url(home),
            "form": _form_string(home_last_5),
            "elo": round(ratings.get(home, 1500.0), 1),
            "last_5": home_last_5,
            "aggregates": _aggregate(home_last_5, home),
        },
        "away_stats": {
            "team": away,
            "logo": logo_url(away),
            "form": _form_string(away_last_5),
            "elo": round(ratings.get(away, 1500.0), 1),
            "last_5": away_last_5,
            "aggregates": _aggregate(away_last_5, away),
        },
    }
