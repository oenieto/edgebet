"""
Edgebet — endpoints de administración.
Permite forzar marcadores de fixtures (Copa del Mundo, etc.) y liquidar apuestas asociadas.
"""
from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.db import connect
from api.auth import UserPublic, get_current_user
from api.settlement import settle_pending_picks

router = APIRouter(prefix="/admin", tags=["admin"])


class ScoreOverrideRequest(BaseModel):
    home_score: int
    away_score: int


def get_current_admin(
    user: Annotated[UserPublic, Depends(get_current_user)]
) -> UserPublic:
    """Valida que el usuario tenga el rol 'admin'."""
    with connect() as cur:
        cur.execute("SELECT role FROM users WHERE id = %s", (user.id,))
        row = cur.fetchone()
        
    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no encontrado o sin rol asignado."
        )
        
    # sqlite3.Row / DictRow / tuple fallback
    role = row["role"] if hasattr(row, "__getitem__") and "role" in row else row[0]
    
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Requiere rol 'admin'."
        )
    return user


@router.post("/picks/regenerate")
def regenerate_picks(
    admin: Annotated[UserPublic, Depends(get_current_admin)]
) -> dict:
    """
    Fuerza la regeneración del pool de picks bajo demanda (rol admin).
    Corre el pipeline completo y persiste en `picks` + `predictions`.
    """
    # Import diferido para no cargar el pipeline pesado al importar el router.
    from api.picks_service import generate_and_persist_picks

    try:
        picks = generate_and_persist_picks()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerando picks: {exc}",
        )
    return {"status": "success", "generated": len(picks or [])}


@router.post("/fixtures/{fixture_id}/override")
def override_fixture_score(
    fixture_id: int,
    body: ScoreOverrideRequest,
    admin: Annotated[UserPublic, Depends(get_current_admin)]
) -> dict:
    """
    Forzar marcador de un partido en la base de datos y correr liquidación de apuestas.
    """
    if body.home_score < 0 or body.away_score < 0:
        raise HTTPException(
            status_code=400,
            detail="Los goles no pueden ser negativos."
        )

    try:
        with connect() as cur:
            # Verificar que el fixture existe
            cur.execute("SELECT id, home_team, away_team FROM fixtures WHERE id = %s", (fixture_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Fixture no encontrado.")

            if hasattr(row, "__getitem__") and "home_team" in row:
                home_team = row["home_team"]
                away_team = row["away_team"]
            else:
                home_team = row[1]
                away_team = row[2]
            match_name = f"{home_team} vs {away_team}"

            # Actualizar marcador y cambiar estado a terminado
            cur.execute(
                """
                UPDATE fixtures
                SET status = 'finished', home_score = %s, away_score = %s, last_synced = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (body.home_score, body.away_score, fixture_id)
            )

        # Disparar automáticamente la liquidación para resolver apuestas pendientes asociadas
        settle_result = settle_pending_picks()
        
        return {
            "status": "success",
            "message": f"Marcador de {match_name} actualizado a {body.home_score}-{body.away_score}.",
            "fixture_id": fixture_id,
            "settlement_run": settle_result
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al sobreescribir marcador: {exc}"
        )
