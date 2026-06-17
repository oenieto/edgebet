from __future__ import annotations

import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import UserPublic, get_current_user
from api.db import connect
from api.ranks import get_user_rank_state, list_user_achievements, settle_bet

router = APIRouter(prefix="/user", tags=["user"])


class UserProfileUpdate(BaseModel):
    risk_profile: str
    bankroll: float
    horizon: str
    favorite_leagues: list[str]


class BankrollSnapshot(BaseModel):
    amount: float
    pnl_day: float
    picks_count: int


class BetRequest(BaseModel):
    pick_id: str
    match: str
    prediction: str
    stake: float
    odds: float
    bet_date: str
    market: str | None = "ML"
    bookmaker: str | None = None


class BetSettleRequest(BaseModel):
    bet_id: int
    result: Literal["win", "loss", "void"]
    pnl: float | None = None


class AlertUpdate(BaseModel):
    alert_type: str
    enabled: bool
    threshold_pct: float


@router.get("/{user_id}/profile")
def get_profile(user_id: int, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    with connect() as cur:
        cur.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
    
    if not row:
        return {
            "risk_profile": "balanced",
            "bankroll": 0.0,
            "horizon": "1mes",
            "stake_pct": 5.0,
            "weekly_limit": 0.0,
            "daily_limit": 0.0,
            "favorite_leagues": []
        }
    
    leagues = []
    if row["favorite_leagues"]:
        try:
            leagues = json.loads(row["favorite_leagues"])
        except json.JSONDecodeError:
            pass
            
    return {
        "risk_profile": row["risk_profile"],
        "bankroll": row["bankroll"],
        "horizon": row["horizon"],
        "stake_pct": row["stake_pct"],
        "weekly_limit": row["weekly_limit"],
        "daily_limit": row["daily_limit"],
        "favorite_leagues": leagues,
    }


@router.post("/{user_id}/profile")
def update_profile(user_id: int, body: UserProfileUpdate, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    stake_pct = 5.0
    if body.risk_profile == "conservative":
        stake_pct = 3.0
    elif body.risk_profile == "aggressive":
        stake_pct = 10.0
        
    weekly_limit = body.bankroll * 0.20
    daily_limit = body.bankroll * 0.10
    
    leagues_json = json.dumps(body.favorite_leagues)
    
    with connect() as cur:
        cur.execute("SELECT id FROM user_profiles WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if row:
            cur.execute(
                """UPDATE user_profiles SET 
                risk_profile=%s, bankroll=%s, horizon=%s, stake_pct=%s, 
                weekly_limit=%s, daily_limit=%s, favorite_leagues=%s, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s""",
                (body.risk_profile, body.bankroll, body.horizon, stake_pct, weekly_limit, daily_limit, leagues_json, user_id)
            )
        else:
            cur.execute(
                """INSERT INTO user_profiles (user_id, risk_profile, bankroll, horizon, stake_pct, weekly_limit, daily_limit, favorite_leagues)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (user_id, body.risk_profile, body.bankroll, body.horizon, stake_pct, weekly_limit, daily_limit, leagues_json)
            )
        cur.execute("UPDATE users SET onboarding_done = true WHERE id = %s", (user_id,))
    
    return {"status": "success"}


@router.get("/{user_id}/bankroll")
def get_bankroll(user_id: int, user: Annotated[UserPublic, Depends(get_current_user)]):
    """Compat: mantiene la forma vieja {current_amount, initial_amount, ...} pero
    lee del sistema NUEVO (tabla bankroll + bankroll_equity_log), que es la única
    fuente de verdad. Fallback legacy a user_profiles/bankroll_snapshots solo si el
    usuario aún no tiene fila en bankroll (no debería pasar tras la migración)."""
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    with connect() as cur:
        cur.execute(
            "SELECT initial_capital, current_balance FROM bankroll WHERE user_id = %s",
            (user_id,),
        )
        bk = cur.fetchone()
        if bk:
            current_amount = float(bk["current_balance"])
            initial = float(bk["initial_capital"])
            cur.execute(
                "SELECT snapshot_date, balance FROM bankroll_equity_log "
                "WHERE user_id = %s ORDER BY snapshot_date ASC LIMIT 30",
                (user_id,),
            )
            sparkline = [
                {
                    "date": r["snapshot_date"].isoformat() if hasattr(r["snapshot_date"], "isoformat") else str(r["snapshot_date"]),
                    "amount": float(r["balance"]),
                }
                for r in cur.fetchall()
            ]
        else:
            # Fallback legacy (pre-migración).
            cur.execute("SELECT bankroll FROM user_profiles WHERE user_id = %s", (user_id,))
            profile = cur.fetchone()
            current_amount = float(profile["bankroll"]) if profile else 0.0
            cur.execute(
                "SELECT date, amount FROM bankroll_snapshots WHERE user_id = %s ORDER BY date ASC LIMIT 30",
                (user_id,),
            )
            sparkline = [{"date": r["date"], "amount": float(r["amount"])} for r in cur.fetchall()]
            initial = sparkline[0]["amount"] if sparkline else current_amount

    pnl_total = current_amount - initial
    pnl_pct = (pnl_total / initial * 100) if initial > 0 else 0

    return {
        "current_amount": current_amount,
        "initial_amount": initial,
        "pnl_total": pnl_total,
        "pnl_pct": pnl_pct,
        "sparkline_data": sparkline,
    }


@router.post("/{user_id}/bankroll/snapshot")
def save_bankroll_snapshot(user_id: int, body: BankrollSnapshot, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    
    with connect() as cur:
        cur.execute(
            """INSERT INTO bankroll_snapshots (user_id, date, amount, pnl_day, picks_count)
            VALUES (%s, %s, %s, %s, %s)""",
            (user_id, today, body.amount, body.pnl_day, body.picks_count)
        )
    return {"status": "success"}


@router.get("/{user_id}/bets")
def get_bets(user_id: int, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    with connect() as cur:
        cur.execute("SELECT * FROM user_bets WHERE user_id = %s ORDER BY bet_date DESC", (user_id,))
        rows = cur.fetchall()
        
    bets = []
    wins = 0
    losses = 0
    pending = 0
    total_pnl = 0.0
    
    for r in rows:
        b = dict(r)
        bets.append(b)
        if b["result"] == "win":
            wins += 1
            total_pnl += (b["pnl"] or 0)
        elif b["result"] == "loss":
            losses += 1
            total_pnl -= b["stake"]
        elif b["result"] == "pending":
            pending += 1
            
    total = wins + losses
    accuracy = (wins / total * 100) if total > 0 else 0.0
    
    return {
        "bets": bets,
        "total_bets": len(bets),
        "wins": wins,
        "losses": losses,
        "pending": pending,
        "accuracy": accuracy,
        "total_pnl": total_pnl,
        "roi_pct": 0.0
    }


@router.post("/{user_id}/bets")
def create_bet(user_id: int, body: BetRequest, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    with connect() as cur:
        cur.execute(
            """INSERT INTO user_bets (user_id, pick_id, match, prediction, market, stake, odds, result, bookmaker, bet_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s) RETURNING id""",
            (user_id, body.pick_id, body.match, body.prediction, (body.market or "ML"),
             body.stake, body.odds, body.bookmaker, body.bet_date),
        )
        row = cur.fetchone()
    return {"status": "success", "bet_id": row["id"] if row else None}


@router.post("/{user_id}/bets/settle")
def settle_user_bet(
    user_id: int,
    body: BetSettleRequest,
    user: Annotated[UserPublic, Depends(get_current_user)],
):
    """
    Liquida una apuesta del usuario y dispara el flujo de XP/rangos/achievements.
    El owner puede settlearse a sí mismo (caso self-reporting). En producción
    debería llamarse desde un job cron que cruza resultados reales.
    """
    if user.id != user_id and user.tier != "vip":
        # Permito a VIP/admin settlear de otros usuarios para QA
        raise HTTPException(status_code=403, detail="Forbidden")

    with connect() as cur:
        cur.execute("SELECT * FROM user_bets WHERE id = %s AND user_id = %s",
                    (body.bet_id, user_id))
        bet = cur.fetchone()
        if not bet:
            raise HTTPException(status_code=404, detail="Bet no encontrada")

        pnl = body.pnl
        if pnl is None:
            stake = float(bet["stake"]); odds = float(bet["odds"] or 0)
            if body.result == "win":
                pnl = stake * (odds - 1.0)
            elif body.result == "loss":
                pnl = -stake
            else:
                pnl = 0.0

        cur.execute(
            "UPDATE user_bets SET result=%s, pnl=%s WHERE id=%s",
            (body.result, pnl, body.bet_id),
        )

    # settle_bet() abre su propia conexión; lo dejamos fuera del bloque anterior
    summary = settle_bet(body.bet_id)
    return {"status": "settled", **summary}


@router.get("/{user_id}/rank")
def get_rank(user_id: int, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id and user.tier != "vip":
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_user_rank_state(user_id)


@router.get("/{user_id}/achievements")
def get_achievements(user_id: int, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id and user.tier != "vip":
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"achievements": list_user_achievements(user_id)}


@router.get("/{user_id}/alerts")
def get_alerts(user_id: int, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    with connect() as cur:
        cur.execute("SELECT * FROM user_alerts WHERE user_id = %s", (user_id,))
        rows = cur.fetchall()
        cur.execute("SELECT weekly_limit FROM user_profiles WHERE user_id = %s", (user_id,))
        profile = cur.fetchone()
        
    weekly_limit = profile["weekly_limit"] if profile else 0.0
    weekly_used = 0.0
    
    return {
        "alerts": [dict(r) for r in rows],
        "weekly_used": weekly_used,
        "weekly_limit": weekly_limit,
        "pct_used": (weekly_used / weekly_limit * 100) if weekly_limit > 0 else 0
    }


@router.post("/{user_id}/alerts")
def update_alert(user_id: int, body: AlertUpdate, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    with connect() as cur:
        cur.execute("SELECT id FROM user_alerts WHERE user_id = %s AND alert_type = %s", (user_id, body.alert_type))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE user_alerts SET enabled = %s, threshold_pct = %s WHERE id = %s",
                (body.enabled, body.threshold_pct, row["id"])
            )
        else:
            cur.execute(
                "INSERT INTO user_alerts (user_id, alert_type, enabled, threshold_pct) VALUES (%s, %s, %s, %s)",
                (user_id, body.alert_type, body.enabled, body.threshold_pct)
            )
    return {"status": "success"}


@router.get("/{user_id}/onboarding-status")
def get_onboarding_status(user_id: int, user: Annotated[UserPublic, Depends(get_current_user)]):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    with connect() as cur:
        cur.execute("SELECT onboarding_done FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        
    done = bool(row["onboarding_done"]) if row else False
    return {"onboarding_done": done, "missing_steps": [] if done else ["profile", "bankroll", "leagues"]}
