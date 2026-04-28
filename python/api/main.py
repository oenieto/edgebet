"""
Edgebet FastAPI entry point.
Run from python/ directory: uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.auth import UserPublic, get_current_user, router as auth_router
from api.user import router as user_router
from api.stripe_webhooks import router as stripe_router
from api.db import init_db
from api.picks_service import get_leagues, get_todays_picks, get_pick_stats
from api.parlay_builder import build_all_tiers

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
    # Warm-up en background: primer usuario ve cache caliente sin bloquear arranque.
    import threading
    def _warm():
        try:
            get_todays_picks()
        except Exception as exc:
            print(f"[startup] warmup falló: {exc}")
    threading.Thread(target=_warm, daemon=True).start()


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
    market: str | None = None
    homeTeam: str
    awayTeam: str
    homeLogo: str | None = None
    awayLogo: str | None = None
    league: str
    leagueSlug: str | None = None
    kickoff: str
    prediction: str
    confidence: int
    mlProb: dict[str, float]
    polyProb: dict[str, float] | None = None
    bkProb: dict[str, float]
    aiReasoning: str
    suggestedStake: float
    status: str
    odds: float | None = None
    edgePp: float | None = None
    evPct: float | None = None
    combos: dict[str, str] | None = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    timestamp: str




@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    model_path = os.path.join(os.path.dirname(__file__), "..", "models")
    has_artifact = any(
        fname.endswith(".pkl") for fname in os.listdir(model_path) if os.path.isdir(model_path)
    ) if os.path.isdir(model_path) else False
    return HealthResponse(
        status="ok",
        model_loaded=has_artifact,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/picks/today", response_model=list[Pick])
def picks_today(league: str | None = None) -> list[Pick]:
    real = get_todays_picks(league_slug=league)
    if real:
        return [Pick(**p) for p in real]
    return []


@app.get("/picks/{pick_id}", response_model=Pick)
def get_pick(pick_id: str) -> Pick:
    picks = get_todays_picks()
    for p in picks:
        if p["id"] == pick_id:
            return Pick(**p)
    raise HTTPException(status_code=404, detail="Pick not found")


class MatchStat(BaseModel):
    date: str
    home: str
    away: str
    homeLogo: str | None = None
    awayLogo: str | None = None
    score: str
    result: str | None = None

class TeamAggregates(BaseModel):
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int

class TeamStats(BaseModel):
    team: str
    logo: str | None = None
    form: str | None = None
    elo: float | None = None
    last_5: list[MatchStat]
    aggregates: TeamAggregates | None = None

class PickStatsResponse(BaseModel):
    h2h: list[MatchStat]
    home_stats: TeamStats
    away_stats: TeamStats

@app.get("/picks/{pick_id}/stats", response_model=PickStatsResponse)
def get_pick_stats_endpoint(pick_id: str) -> PickStatsResponse:
    stats = get_pick_stats(pick_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Stats not found")
    return PickStatsResponse(**stats)


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
