from __future__ import annotations

import psycopg2
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from api.auth import UserPublic, get_current_user
from api.db import connect
import json

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
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    with connect() as cur:
        cur.execute("SELECT bankroll FROM user_profiles WHERE user_id = %s", (user_id,))
        profile = cur.fetchone()
        current_amount = profile["bankroll"] if profile else 0.0
        
        cur.execute("SELECT * FROM bankroll_snapshots WHERE user_id = %s ORDER BY date ASC LIMIT 30", (user_id,))
        rows = cur.fetchall()
        
    sparkline = [{"date": r["date"], "amount": r["amount"]} for r in rows]
    initial = sparkline[0]["amount"] if sparkline else current_amount
    pnl_total = current_amount - initial
    pnl_pct = (pnl_total / initial * 100) if initial > 0 else 0
    
    return {
        "current_amount": current_amount,
        "initial_amount": initial,
        "pnl_total": pnl_total,
        "pnl_pct": pnl_pct,
        "sparkline_data": sparkline
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
            """INSERT INTO user_bets (user_id, pick_id, match, prediction, stake, odds, result, bet_date)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s)""",
            (user_id, body.pick_id, body.match, body.prediction, body.stake, body.odds, body.bet_date)
        )
    return {"status": "success"}


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
