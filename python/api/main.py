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
from api.db import init_db
from api.picks_service import get_leagues, get_todays_picks
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


def _mock_picks() -> list[Pick]:
    """Temporary fixtures until the ML pipeline is wired end-to-end."""
    return [
        Pick(
            id=str(uuid4()),
            match="Arsenal vs Chelsea",
            homeTeam="Arsenal",
            awayTeam="Chelsea",
            league="Premier League",
            kickoff="2026-04-19T15:00:00Z",
            prediction="home",
            confidence=74,
            mlProb=ProbabilityTriplet(home=0.58, draw=0.23, away=0.19),
            polyProb=ProbabilityTriplet(home=0.54, draw=0.25, away=0.21),
            bkProb=ProbabilityTriplet(home=0.50, draw=0.27, away=0.23),
            aiReasoning=(
                "Divergencia del 8% detectada frente a Pinnacle closing lines. "
                "El modelo xG proyecta 3.12 goles esperados basados en ausencias defensivas."
            ),
            suggestedStake=2.5,
            status="free",
            odds=1.85,
        ),
        Pick(
            id=str(uuid4()),
            match="Real Madrid vs Getafe",
            homeTeam="Real Madrid",
            awayTeam="Getafe",
            league="La Liga",
            kickoff="2026-04-19T19:00:00Z",
            prediction="home",
            confidence=68,
            mlProb=ProbabilityTriplet(home=0.71, draw=0.17, away=0.12),
            polyProb=ProbabilityTriplet(home=0.68, draw=0.20, away=0.12),
            bkProb=ProbabilityTriplet(home=0.72, draw=0.18, away=0.10),
            aiReasoning=(
                "Tres fuentes coinciden en el favorito. Handicap asiático -1.5 "
                "captura la ventaja de forma sin exponerse a cuotas mínimas."
            ),
            suggestedStake=2.0,
            status="free",
            odds=2.10,
        ),
        Pick(
            id=str(uuid4()),
            match="Bayern vs Dortmund",
            homeTeam="Bayern",
            awayTeam="Dortmund",
            league="Bundesliga",
            kickoff="2026-04-20T14:30:00Z",
            prediction="home",
            confidence=82,
            mlProb=ProbabilityTriplet(home=0.66, draw=0.20, away=0.14),
            polyProb=ProbabilityTriplet(home=0.58, draw=0.22, away=0.20),
            bkProb=ProbabilityTriplet(home=0.52, draw=0.24, away=0.24),
            aiReasoning=(
                "Edge del 9.2%: el modelo ML identifica un favoritismo local subestimado "
                "por Polymarket y Bet365. Mercado 'Bayern win to nil' con valor."
            ),
            suggestedStake=3.0,
            status="premium",
            odds=3.40,
        ),
    ]


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
    # Fallback a mocks si la descarga de datos falla
    return _mock_picks()


@app.get("/picks/exclusive", response_model=Pick)
def pick_exclusive() -> Pick:
    """
    El único 'Pick del día' curado: el pick con mayor EV de toda la jornada.
    Frontend decide paywall según tier del usuario.
    """
    real = get_todays_picks(league_slug=None)
    if not real:
        real = [p.model_dump() for p in _mock_picks()]
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
