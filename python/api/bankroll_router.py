"""
Edgebet — módulo de bankroll: capital, movimientos y curva de equity.

Sistema persistido en DB (tablas bankroll / bankroll_transactions /
bankroll_equity_log), independiente del widget store-based previo
(components/bankroll/BankrollTracker). Todos los endpoints requieren JWT.

Las funciones `ensure_bankroll` / `apply_transaction` / `upsert_equity` operan
sobre un cursor abierto para que settlement.py pueda reusarlas dentro de su
propia transacción al liquidar apuestas.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import UserPublic, get_current_user
from api.db import connect

router = APIRouter(prefix="/bankroll", tags=["bankroll"])

_DEFAULT_CAPITAL = 1000.0
_TX_TYPES = {
    "deposit", "withdrawal", "bet_placed", "bet_won", "bet_lost", "bet_void", "adjustment",
}


# ===========================================================================
# Helpers reutilizables (operan sobre un cursor abierto)
# ===========================================================================
def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def ensure_bankroll(cur, user_id: int, initial_capital: float = _DEFAULT_CAPITAL,
                    currency: str = "USD") -> dict:
    """Devuelve la fila de bankroll del usuario, creándola si no existe."""
    cur.execute(
        "SELECT initial_capital, current_balance, currency FROM bankroll WHERE user_id=%s",
        (user_id,),
    )
    row = cur.fetchone()
    if row:
        return {
            "initial_capital": float(row["initial_capital"]),
            "current_balance": float(row["current_balance"]),
            "currency": row["currency"],
        }
    cur.execute(
        """
        INSERT INTO bankroll (user_id, initial_capital, current_balance, currency)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, initial_capital, initial_capital, currency),
    )
    upsert_equity(cur, user_id, _today_iso(), initial_capital)
    return {"initial_capital": initial_capital, "current_balance": initial_capital, "currency": currency}


def upsert_equity(cur, user_id: int, snapshot_date: str, balance: float) -> None:
    """Inserta/actualiza el snapshot de equity de un día (idempotente)."""
    cur.execute(
        "SELECT id FROM bankroll_equity_log WHERE user_id=%s AND snapshot_date=%s",
        (user_id, snapshot_date),
    )
    if cur.fetchone():
        cur.execute(
            "UPDATE bankroll_equity_log SET balance=%s WHERE user_id=%s AND snapshot_date=%s",
            (balance, user_id, snapshot_date),
        )
    else:
        cur.execute(
            "INSERT INTO bankroll_equity_log (user_id, snapshot_date, balance) VALUES (%s, %s, %s)",
            (user_id, snapshot_date, balance),
        )


def apply_transaction(cur, user_id: int, tx_type: str, amount: float,
                      note: Optional[str] = None, reference_id: Optional[int] = None) -> float:
    """Aplica un movimiento: actualiza balance, registra la transacción y refresca
    el snapshot de equity de hoy. Devuelve el balance resultante.

    `amount` con signo: positivo = crédito, negativo = débito. Auto-crea el
    bankroll del usuario si no existe (usuarios previos al módulo).
    """
    state = ensure_bankroll(cur, user_id)
    new_balance = round(state["current_balance"] + amount, 4)

    cur.execute(
        "UPDATE bankroll SET current_balance=%s, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s",
        (new_balance, user_id),
    )
    cur.execute(
        """
        INSERT INTO bankroll_transactions (user_id, type, amount, balance_after, reference_id, note)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, tx_type, round(amount, 4), new_balance, reference_id, note),
    )
    upsert_equity(cur, user_id, _today_iso(), new_balance)
    return new_balance


# ===========================================================================
# Modelos de request
# ===========================================================================
class SetupRequest(BaseModel):
    initial_capital: float = _DEFAULT_CAPITAL
    currency: str = "USD"


class MovementRequest(BaseModel):
    amount: float
    note: Optional[str] = None


# ===========================================================================
# Cómputo del summary
# ===========================================================================
def _compute_summary(cur, user_id: int) -> dict:
    bk = ensure_bankroll(cur, user_id)
    initial = bk["initial_capital"]
    current = bk["current_balance"]

    cur.execute(
        """
        SELECT match, prediction, stake, odds, result, pnl, settled_at, created_at
        FROM user_bets
        WHERE user_id=%s AND result IN ('win','loss','void')
        ORDER BY COALESCE(settled_at, created_at) ASC
        """,
        (user_id,),
    )
    bets = cur.fetchall()

    won = lost = void = 0
    odds_vals: list[float] = []
    stake_vals: list[float] = []
    best = worst = None
    seq: list[str] = []  # 'win'/'loss' en orden cronológico para rachas

    for b in bets:
        result = b["result"]
        stake = float(b["stake"] or 0)
        odds = float(b["odds"]) if b["odds"] is not None else None
        pnl = float(b["pnl"]) if b["pnl"] is not None else 0.0
        match = b["match"]

        if result == "win":
            won += 1
            seq.append("win")
        elif result == "loss":
            lost += 1
            seq.append("loss")
        else:
            void += 1

        if odds is not None:
            odds_vals.append(odds)
        if stake:
            stake_vals.append(stake)

        if best is None or pnl > best["profit"]:
            best = {"match": match, "profit": round(pnl, 2), "odds": odds}
        if worst is None or pnl < worst["profit"]:
            worst = {"match": match, "profit": round(pnl, 2), "odds": odds}

    total_settled = won + lost + void
    decided = won + lost
    win_rate = round(won / decided * 100, 2) if decided else 0.0
    total_pnl = round(current - initial, 2)
    total_pnl_pct = round(total_pnl / initial * 100, 2) if initial else 0.0
    total_staked = sum(stake_vals)
    bet_pnl = sum(float(b["pnl"] or 0) for b in bets)
    roi = round(bet_pnl / total_staked * 100, 2) if total_staked else 0.0

    cur_streak, longest_win, longest_loss = _streaks(seq)

    return {
        "initial_capital": round(initial, 2),
        "current_balance": round(current, 2),
        "currency": bk["currency"],
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "roi": roi,
        "total_bets": total_settled,
        "won": won,
        "lost": lost,
        "void": void,
        "win_rate": win_rate,
        "current_streak": cur_streak,
        "longest_win_streak": longest_win,
        "longest_loss_streak": longest_loss,
        "avg_odds": round(sum(odds_vals) / len(odds_vals), 2) if odds_vals else 0.0,
        "avg_stake": round(sum(stake_vals) / len(stake_vals), 2) if stake_vals else 0.0,
        "best_bet": best,
        "worst_bet": worst,
        "equity_log": _equity_series(cur, user_id, days=90),
    }


def _streaks(seq: list[str]) -> tuple[int, int, int]:
    """Devuelve (racha_actual, mejor_racha_ganadora, peor_racha_perdedora).
    racha_actual: positiva = victorias, negativa = derrotas."""
    longest_win = longest_loss = 0
    run = 0
    last = None
    for r in seq:
        if r == last:
            run += 1
        else:
            run = 1
            last = r
        if r == "win":
            longest_win = max(longest_win, run)
        else:
            longest_loss = max(longest_loss, run)
    # Racha actual = run final con signo
    current = 0
    for r in reversed(seq):
        if not seq:
            break
        if r == seq[-1]:
            current += 1
        else:
            break
    if seq and seq[-1] == "loss":
        current = -current
    return current, longest_win, longest_loss


def _equity_series(cur, user_id: int, days: int) -> list[dict]:
    """Serie de equity de los últimos `days` días, rellenando huecos con el
    último balance conocido (forward-fill)."""
    cur.execute(
        "SELECT snapshot_date, balance FROM bankroll_equity_log WHERE user_id=%s ORDER BY snapshot_date ASC",
        (user_id,),
    )
    rows = cur.fetchall()
    by_date: dict[str, float] = {}
    for r in rows:
        d = r["snapshot_date"]
        d = d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]
        by_date[d] = float(r["balance"])

    if not by_date:
        return []

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    # Balance de arranque: último snapshot anterior a la ventana.
    last_balance = None
    for d in sorted(by_date):
        if d < start.isoformat():
            last_balance = by_date[d]
    out: list[dict] = []
    cursor_day = start
    while cursor_day <= end:
        key = cursor_day.isoformat()
        if key in by_date:
            last_balance = by_date[key]
        if last_balance is not None:
            out.append({"date": key, "balance": round(last_balance, 2)})
        cursor_day += timedelta(days=1)
    return out


# ===========================================================================
# Endpoints
# ===========================================================================
@router.get("/summary")
def bankroll_summary(user: Annotated[UserPublic, Depends(get_current_user)]) -> dict:
    """Resumen del bankroll. Si el usuario aún no lo configuró devuelve
    {configured: false} (sin auto-crear) para que el frontend muestre el CTA."""
    with connect() as cur:
        cur.execute("SELECT id FROM bankroll WHERE user_id=%s", (user.id,))
        if not cur.fetchone():
            return {"configured": False}
        summary = _compute_summary(cur, user.id)
        summary["configured"] = True
        return summary


@router.post("/setup")
def bankroll_setup(body: SetupRequest,
                   user: Annotated[UserPublic, Depends(get_current_user)]) -> dict:
    if body.initial_capital <= 0:
        raise HTTPException(status_code=400, detail="El capital inicial debe ser > 0.")
    with connect() as cur:
        cur.execute("SELECT id FROM bankroll WHERE user_id=%s", (user.id,))
        exists = cur.fetchone()
        if exists:
            # Reset explícito: reinicia capital y limpia historial.
            cur.execute(
                """
                UPDATE bankroll SET initial_capital=%s, current_balance=%s, currency=%s,
                    updated_at=CURRENT_TIMESTAMP WHERE user_id=%s
                """,
                (body.initial_capital, body.initial_capital, body.currency, user.id),
            )
            cur.execute("DELETE FROM bankroll_transactions WHERE user_id=%s", (user.id,))
            cur.execute("DELETE FROM bankroll_equity_log WHERE user_id=%s", (user.id,))
        else:
            cur.execute(
                """
                INSERT INTO bankroll (user_id, initial_capital, current_balance, currency)
                VALUES (%s, %s, %s, %s)
                """,
                (user.id, body.initial_capital, body.initial_capital, body.currency),
            )
        upsert_equity(cur, user.id, _today_iso(), body.initial_capital)
        return _compute_summary(cur, user.id)


@router.post("/deposit")
def bankroll_deposit(body: MovementRequest,
                     user: Annotated[UserPublic, Depends(get_current_user)]) -> dict:
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser > 0.")
    with connect() as cur:
        apply_transaction(cur, user.id, "deposit", abs(body.amount), note=body.note)
        return _compute_summary(cur, user.id)


@router.post("/withdraw")
def bankroll_withdraw(body: MovementRequest,
                      user: Annotated[UserPublic, Depends(get_current_user)]) -> dict:
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser > 0.")
    with connect() as cur:
        state = ensure_bankroll(cur, user.id)
        if body.amount > state["current_balance"]:
            raise HTTPException(status_code=400, detail="Monto mayor al balance disponible.")
        apply_transaction(cur, user.id, "withdrawal", -abs(body.amount), note=body.note)
        return _compute_summary(cur, user.id)


@router.get("/transactions")
def bankroll_transactions(
    user: Annotated[UserPublic, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    with connect() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM bankroll_transactions WHERE user_id=%s", (user.id,))
        total = int(cur.fetchone()["n"])
        offset = (page - 1) * limit
        cur.execute(
            """
            SELECT id, type, amount, balance_after, reference_id, note, created_at
            FROM bankroll_transactions
            WHERE user_id=%s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            (user.id, limit, offset),
        )
        txs = []
        for r in cur.fetchall():
            created = r["created_at"]
            txs.append({
                "id": r["id"],
                "type": r["type"],
                "amount": float(r["amount"]),
                "balance_after": float(r["balance_after"]),
                "reference_id": r["reference_id"],
                "note": r["note"],
                "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
            })
        return {"total": total, "page": page, "transactions": txs}


@router.get("/equity")
def bankroll_equity(
    user: Annotated[UserPublic, Depends(get_current_user)],
    days: int = Query(90, ge=1, le=365),
) -> dict:
    with connect() as cur:
        ensure_bankroll(cur, user.id)
        return {"days": days, "equity": _equity_series(cur, user.id, days=days)}
