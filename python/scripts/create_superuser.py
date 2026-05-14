"""
Edgebet — script idempotente para crear/actualizar el superusuario.

Uso desde /python:
  .venv/bin/python -m scripts.create_superuser
  .venv/bin/python -m scripts.create_superuser --email admin@edgebet.dev --password Edgebet2026!

Comportamiento:
  - Si el email no existe → crea usuario con tier=vip, role=admin, onboarding_done=true.
  - Si existe → upgrade in place (tier=vip, role=admin) sin resetear password ni datos.
  - Crea (si faltan): user_profile con bankroll demo, user_ranks con tier máximo,
    bankroll_snapshot inicial. Todo opcional para que el dashboard se vea con datos.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Permite ejecutar tanto desde /python como desde la raíz del repo
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bcrypt  # noqa: E402

from api.db import init_db, connect  # noqa: E402
from api.ranks import ensure_user_rank_row  # noqa: E402


DEFAULT_EMAIL = "admin@edgebet.dev"
DEFAULT_PASSWORD = "Edgebet2026!"
DEFAULT_NAME = "Edgebet Admin"


def _hash_password(pw: str) -> str:
    pw_bytes = pw.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def upsert_superuser(email: str, password: str, name: str) -> int:
    email_norm = email.strip().lower()
    pw_hash = _hash_password(password)

    with connect() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (email_norm,))
        row = cur.fetchone()
        if row:
            user_id = row["id"]
            cur.execute(
                "UPDATE users SET tier='vip', role='admin', name=%s, "
                "password_hash=%s, onboarding_done=1 WHERE id=%s",
                (name, pw_hash, user_id),
            )
            print(f"[superuser] upgrade en place — id={user_id} email={email_norm} password={password}")
        else:
            cur.execute(
                "INSERT INTO users (email, password_hash, name, tier, role, onboarding_done) "
                "VALUES (%s, %s, %s, 'vip', 'admin', 1) RETURNING id",
                (email_norm, pw_hash, name),
            )
            res = cur.fetchone()
            user_id = res["id"]
            print(f"[superuser] creado — id={user_id} email={email_norm} password={password}")
    return user_id


def seed_demo_profile(user_id: int) -> None:
    """Profile con bankroll listo + sparkline 14d para que el dashboard se vea poblado."""
    with connect() as cur:
        cur.execute("SELECT id FROM user_profiles WHERE user_id=%s", (user_id,))
        if cur.fetchone():
            print("[superuser] profile ya existe, lo respeto")
            return
        cur.execute("""
            INSERT INTO user_profiles
            (user_id, risk_profile, bankroll, horizon, stake_pct, weekly_limit, daily_limit, favorite_leagues)
            VALUES (%s, 'aggressive', 5000.0, '6meses', 8.0, 1000.0, 500.0, %s)
        """, (user_id, json.dumps([
            "premier-league", "la-liga", "champions-league", "bundesliga", "serie-a",
        ])))
        print("[superuser] profile demo insertado (bankroll $5000, perfil aggressive)")


def seed_demo_bankroll_history(user_id: int) -> None:
    """14 snapshots con curva ascendente para mostrar el sparkline funcionando."""
    with connect() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM bankroll_snapshots WHERE user_id=%s", (user_id,))
        if cur.fetchone()["c"] > 0:
            return
        base = 4000.0
        today = datetime.utcnow().date()
        # Curva con 12% upside total y volatilidad ligera — realista
        values = [base, 4080, 4055, 4140, 4210, 4180, 4290, 4350, 4420, 4380, 4500, 4630, 4720, 5000]
        for i, amount in enumerate(values):
            d = (today - timedelta(days=len(values) - 1 - i)).isoformat()
            cur.execute("""
                INSERT INTO bankroll_snapshots (user_id, date, amount, pnl_day, picks_count)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, d, amount, amount - (values[i-1] if i else amount), 2))
        print(f"[superuser] {len(values)} snapshots de bankroll insertados")


def seed_max_rank(user_id: int) -> None:
    """Rango Legend + XP suficiente para mostrar la barra completa al 100%."""
    ensure_user_rank_row(user_id)
    with connect() as cur:
        cur.execute("""
            UPDATE user_ranks
            SET current_rank_code='legend', total_xp=15000,
                bets_won=84, bets_lost=42, longshot_wins=12,
                biggest_win_odds=8.50, streak_current=4, streak_best=11
            WHERE user_id=%s
        """, (user_id,))
        # rank_history para que el perfil muestre el camino recorrido
        cur.execute("SELECT COUNT(*) AS c FROM rank_history WHERE user_id=%s", (user_id,))
        if cur.fetchone()["c"] == 0:
            milestones = [
                ("rookie", "analyst", 100),
                ("analyst", "strategist", 300),
                ("strategist", "quant", 700),
                ("quant", "sharpshooter", 1500),
                ("sharpshooter", "edge_hunter", 3000),
                ("edge_hunter", "master", 6000),
                ("master", "legend", 12000),
            ]
            for from_r, to_r, xp in milestones:
                cur.execute("""
                    INSERT INTO rank_history (user_id, from_rank, to_rank, direction, total_xp_at_event)
                    VALUES (%s, %s, %s, 'up', %s)
                """, (user_id, from_r, to_r, xp))
            print(f"[superuser] {len(milestones)} entradas de rank_history insertadas")


def seed_all_achievements(user_id: int) -> None:
    """Marca todos los achievements como desbloqueados — vitrina full para QA."""
    with connect() as cur:
        cur.execute("SELECT code FROM achievements")
        codes = [r["code"] for r in cur.fetchall()]
        cur.execute("SELECT achievement_code FROM user_achievements WHERE user_id=%s", (user_id,))
        already = {r["achievement_code"] for r in cur.fetchall()}
        new = [c for c in codes if c not in already]
        for code in new:
            cur.execute(
                "INSERT INTO user_achievements (user_id, achievement_code) VALUES (%s, %s)",
                (user_id, code),
            )
        if new:
            print(f"[superuser] {len(new)} achievements desbloqueados")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea/actualiza el superusuario de Edgebet")
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--minimal", action="store_true",
                        help="Crea solo el user, sin demo data ni achievements")
    args = parser.parse_args()

    init_db()
    user_id = upsert_superuser(args.email, args.password, args.name)
    if not args.minimal:
        seed_demo_profile(user_id)
        seed_demo_bankroll_history(user_id)
        seed_max_rank(user_id)
        seed_all_achievements(user_id)
    print()
    print("=" * 60)
    print(f"  ✓ Superuser listo")
    print(f"  email:    {args.email}")
    print(f"  password: {args.password}")
    print(f"  tier:     vip   role: admin   onboarding: done")
    print("=" * 60)


if __name__ == "__main__":
    main()
