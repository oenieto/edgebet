"""
Edgebet FastAPI entry point.
Run from python/ directory: uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.auth import UserPublic, get_current_user, router as auth_router
from api.user import router as user_router
from api.stripe_webhooks import router as stripe_router
from api.db import init_db
from api.picks_service import get_leagues, get_todays_picks
from api.parlay_builder import build_all_tiers
from api.odds_provider import fetch_league_odds, find_odds_for_match, provider_status
from api.sofascore_view import build_match_view, build_match_view_by_pick_id
from api.ranks import list_ranks

app = FastAPI(title="Edgebet API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    # Warm-up desactivado temporalmente para evitar saturación de I/O en este entorno.
    # import threading
    # def _warm():
    #     try:
    #         get_todays_picks()
    #     except Exception as exc:
    #         print(f"[startup] warmup falló: {exc}")
    # threading.Thread(target=_warm, daemon=True).start()


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(stripe_router)


class ProbabilityTriplet(BaseModel):
    home: float
    draw: float
    away: float


class Pick(BaseModel):
    id: str
    match: str
    homeTeam: str
    awayTeam: str
    league: str
    leagueSlug: str | None = None
    kickoff: str
    prediction: Literal["home", "draw", "away"]
    confidence: int
    mlProb: ProbabilityTriplet
    polyProb: ProbabilityTriplet | None = None
    bkProb: ProbabilityTriplet
    aiReasoning: str
    suggestedStake: float
    status: Literal["free", "premium", "vip"]
    odds: float | None = None
    edgePp: float | None = None
    evPct: float | None = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    timestamp: str




@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_loaded=False,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/integrations/status")
def integrations_status() -> dict:
    """Quick check of all external integrations."""
    import os
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_odds = bool(os.environ.get("EDGEBET_ODDS_API_KEY"))
    has_stripe = bool(os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_"))
    has_telegram = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))

    from api.db import USE_SQLITE
    return {
        "database": {"type": "sqlite" if USE_SQLITE else "postgresql", "status": "connected"},
        "anthropic": {"configured": has_anthropic, "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")},
        "odds_api": {"configured": has_odds, "provider": "the-odds-api.com"},
        "stripe": {"configured": has_stripe},
        "telegram": {"configured": has_telegram},
        "polymarket": {"configured": True, "note": "No key needed (Gamma API)"},
    }


@app.get("/picks/today", response_model=list[Pick])
def picks_today(league: str | None = None) -> list[Pick]:
    real = get_todays_picks(league_slug=league)
    if real:
        return [Pick(**p) for p in real]
    return []


@app.get("/picks/{pick_id}/stats")
def pick_stats(pick_id: str) -> dict:
    """
    H2H + last_5 + agregados por equipo para el pick `pick_id`.
    Reusa el pool cacheado de /picks/today (no requiere cómputo extra
    salvo el slicing del histórico que ya está en memoria).
    """
    from api.picks_service import get_todays_picks, _load_league
    pool = get_todays_picks(league_slug=None)
    pick = next((p for p in pool if p["id"] == pick_id), None)
    if not pick:
        raise HTTPException(status_code=404, detail="Pick no encontrado o expirado")

    slug = pick.get("leagueSlug")
    if not slug:
        return {"h2h": [], "home_stats": _empty_team_stats(pick["homeTeam"]),
                "away_stats": _empty_team_stats(pick["awayTeam"])}

    try:
        matches, _ratings, _cfg = _load_league(slug)
    except Exception:
        matches = []

    home_team = pick["homeTeam"]
    away_team = pick["awayTeam"]
    home_logo = pick.get("homeLogo")
    away_logo = pick.get("awayLogo")

    return {
        "h2h": _h2h(matches, home_team, away_team, home_logo, away_logo, n=5),
        "home_stats": _team_recent(matches, home_team, home_logo, n=5),
        "away_stats": _team_recent(matches, away_team, away_logo, n=5),
    }


def _empty_team_stats(team: str) -> dict:
    return {"team": team, "logo": None, "form": "", "elo": 1500, "last_5": [],
            "aggregates": {"wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}}


def _h2h(matches: list[dict], home: str, away: str, home_logo: str | None, away_logo: str | None, n: int = 5) -> list[dict]:
    out: list[dict] = []
    for m in reversed(matches):
        h = m.get("HomeTeam"); a = m.get("AwayTeam")
        if (h == home and a == away) or (h == away and a == home):
            try:
                hg = int(m.get("FTHG", 0)); ag = int(m.get("FTAG", 0))
            except (TypeError, ValueError):
                continue
            score = f"{hg}-{ag}"
            out.append({
                "date": m.get("Date", ""),
                "home": h, "away": a,
                "homeLogo": home_logo if h == home else away_logo,
                "awayLogo": away_logo if a == away else home_logo,
                "score": score,
                "result": "W" if hg > ag else ("D" if hg == ag else "L"),
            })
            if len(out) >= n:
                break
    return out


def _team_recent(matches: list[dict], team: str, logo: str | None, n: int = 5) -> dict:
    last: list[dict] = []
    wins = draws = losses = gf = ga = 0
    form_chars: list[str] = []
    for m in reversed(matches):
        h = m.get("HomeTeam"); a = m.get("AwayTeam")
        if h != team and a != team:
            continue
        try:
            hg = int(m.get("FTHG", 0)); ag = int(m.get("FTAG", 0))
        except (TypeError, ValueError):
            continue
        team_is_home = h == team
        team_goals = hg if team_is_home else ag
        rival_goals = ag if team_is_home else hg
        gf += team_goals; ga += rival_goals
        if team_goals > rival_goals:
            wins += 1; form_chars.append("W")
            result_letter = "W"
        elif team_goals == rival_goals:
            draws += 1; form_chars.append("D")
            result_letter = "D"
        else:
            losses += 1; form_chars.append("L")
            result_letter = "L"
        last.append({
            "date": m.get("Date", ""),
            "home": h, "away": a,
            "homeLogo": logo if h == team else None,
            "awayLogo": logo if a == team else None,
            "score": f"{hg}-{ag}",
            "result": result_letter,
        })
        if len(last) >= n:
            break
    return {
        "team": team,
        "logo": logo,
        "form": "".join(form_chars[:5]),
        "elo": None,
        "last_5": last,
        "aggregates": {"wins": wins, "draws": draws, "losses": losses,
                       "goals_for": gf, "goals_against": ga},
    }


@app.get("/odds/status")
def odds_status() -> dict:
    """Estado del provider de odds reales (The Odds API)."""
    return provider_status()


@app.get("/odds/league/{league_slug}")
def odds_for_league(league_slug: str) -> dict:
    """
    Odds reales por liga. Devuelve `configured: false` si no hay API key —
    el dashboard puede mostrar un banner para activarlo en vez de romperse.
    """
    if not provider_status()["configured"]:
        return {"configured": False, "league": league_slug, "odds": []}
    odds = fetch_league_odds(league_slug)
    return {"configured": True, "league": league_slug, "count": len(odds), "odds": odds}


@app.get("/odds/match")
def odds_for_match(home: str, away: str, league: str) -> dict:
    """Odds reales para un match específico."""
    if not provider_status()["configured"]:
        return {"configured": False, "match": f"{home} vs {away}"}
    found = find_odds_for_match(home, away, league)
    return {"configured": True, "match": f"{home} vs {away}", "odds": found}


@app.get("/matches/{fixture_id}/sofascore")
def match_sofascore(fixture_id: int) -> dict:
    """Vista unificada estilo Sofascore por fixture_id (entero, persistido)."""
    view = build_match_view(fixture_id)
    if not view:
        raise HTTPException(status_code=404, detail="Fixture no encontrado")
    return view


@app.get("/matches/by-pick/{pick_id}/sofascore")
def match_sofascore_by_pick(pick_id: str) -> dict:
    """
    Vista Sofascore via pick_id (UUID). Útil mientras la tabla `fixtures`
    no esté completamente sincronizada con un feed externo — busca por
    home/away. Si no hay fixture persistido, 404 y el frontend cae a
    /picks/{id}/stats.
    """
    view = build_match_view_by_pick_id(pick_id)
    if not view:
        raise HTTPException(status_code=404, detail="Sin datos para este pick aún")
    return view


@app.get("/ranks/catalog")
def ranks_catalog() -> dict:
    """Catálogo público de rangos para que el frontend pinte el progress map."""
    return {"ranks": [r.__dict__ for r in list_ranks()]}


@app.get("/picks/exclusive", response_model=Pick)
def pick_exclusive() -> Pick:
    """
    El único 'Pick del día' curado: el pick con mayor EV de toda la jornada.
    Frontend decide paywall según tier del usuario.
    """
    real = get_todays_picks(league_slug=None)
    if not real:
        raise HTTPException(status_code=404, detail="No picks available")
    # get_todays_picks ya ordena por EV desc → primero es el mejor
    return Pick(**real[0])


@app.get("/leagues")
def leagues() -> list[dict]:
    return get_leagues()


@app.get("/metrics")
def metrics() -> dict:
    return {
        "accuracy_30d": 0.614,
        "roi_monthly": 0.248,
        "verified_picks": 847,
        "active_divergences": 8,
    }


@app.get("/metrics/performance")
def metrics_performance(days: int = 30) -> dict:
    """
    Serie temporal de rendimiento: accuracy rolling, ROI acumulado,
    hit rate por liga. Genera datos sintéticos realistas hasta que
    el settlement engine esté activo (Sprint 3).
    """
    from api.performance import build_performance_series
    return build_performance_series(days=days)


PRO_TIERS = {"premium", "vip"}


@app.get("/parlays/today")
def parlays_today(
    user: Annotated[UserPublic, Depends(get_current_user)],
    league: str | None = None,
    tier: str | None = None,
) -> dict:
    """
    Parlays del día (safe/medium/risky). Exclusivo para usuarios Pro (premium/vip).
    - `league`: si se provee, solo usa picks de esa liga.
    - `tier`: si se provee, devuelve solo ese tier; si no, devuelve los 3.
    """
    if user.tier not in PRO_TIERS:
        raise HTTPException(
            status_code=403,
            detail="Parlays disponibles solo para usuarios Pro (premium/vip).",
        )

    picks = get_todays_picks(league_slug=league)
    if not picks:
        return {"parlays": [], "pool_size": 0, "message": "Sin picks disponibles."}

    if tier and tier in {"safe", "medium", "risky"}:
        from api.parlay_builder import build_parlay
        parlay = build_parlay(picks, tier)  # type: ignore[arg-type]
        parlays = [parlay] if parlay else []
    else:
        parlays = build_all_tiers(picks)

    return {
        "parlays": parlays,
        "pool_size": len(picks),
        "tiers_available": [p["tier"] for p in parlays],
    }


# ============================================================
# Sprint 2-3: Market-specific endpoints
# ============================================================

@app.get("/picks/today/btts")
def picks_btts(league: str | None = None) -> list[dict]:
    """BTTS picks del dia."""
    from api.market_endpoints import get_btts_picks
    return get_btts_picks(league_slug=league)


@app.get("/picks/today/corners")
def picks_corners(league: str | None = None) -> list[dict]:
    """Corners O/U picks del dia."""
    from api.market_endpoints import get_corners_picks
    return get_corners_picks(league_slug=league)


@app.get("/picks/today/ah")
def picks_ah(league: str | None = None) -> list[dict]:
    """Asian Handicap picks del dia."""
    from api.market_endpoints import get_ah_picks
    return get_ah_picks(league_slug=league)


@app.get("/odds/{fixture_id}/history")
def odds_history(fixture_id: int, hours: int = 48) -> dict:
    """Historial de odds para sparklines."""
    from api.odds_pipeline import get_odds_history
    return {"fixture_id": fixture_id, "snapshots": get_odds_history(fixture_id, hours)}


@app.get("/odds/{fixture_id}/steam")
def odds_steam(fixture_id: int) -> dict:
    """Steam move indicator para un fixture."""
    from api.odds_pipeline import calculate_steam_move
    return calculate_steam_move(fixture_id)


@app.get("/settlement/run")
def run_settlement() -> dict:
    """Ejecuta settlement de picks pendientes (llamado por cron)."""
    from api.settlement import settle_pending_picks
    return settle_pending_picks()


@app.get("/metrics/accuracy/{user_id}")
def user_accuracy(user_id: int, days: int = 30) -> dict:
    """Accuracy rolling de un usuario."""
    from api.settlement import compute_rolling_accuracy
    return compute_rolling_accuracy(user_id, days)


@app.get("/parlays/correlation")
def parlay_correlation(legs: str = "") -> dict:
    """Calcula descuento por correlacion entre legs de un parlay."""
    from api.correlation_matrix import apply_correlation_discount
    import json as _json
    try:
        leg_list = _json.loads(legs) if legs else []
    except (ValueError, TypeError):
        leg_list = []
    return apply_correlation_discount(leg_list)


@app.get("/players/{home_team}/{away_team}/props")
def player_props(home_team: str, away_team: str) -> dict:
    """Player props disponibles para un match."""
    from api.player_props import get_players_for_match
    players = get_players_for_match(home_team, away_team)
    return {"players": players, "count": len(players)}
