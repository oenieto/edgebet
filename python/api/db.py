"""
PostgreSQL setup para Edgebet.
"""
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://edgebet:edgebet@localhost:5432/edgebet"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    onboarding_done BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    risk_profile TEXT DEFAULT 'balanced',
    bankroll REAL DEFAULT 0,
    horizon TEXT DEFAULT '1mes',
    stake_pct REAL DEFAULT 5.0,
    weekly_limit REAL,
    daily_limit REAL,
    favorite_leagues TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bankroll_snapshots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    pnl_day REAL DEFAULT 0,
    picks_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_bets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    pick_id TEXT NOT NULL,
    match TEXT NOT NULL,
    prediction TEXT NOT NULL,
    stake REAL NOT NULL,
    odds REAL,
    result TEXT,
    pnl REAL,
    bet_date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    alert_type TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    threshold_pct REAL,
    triggered_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    country_id TEXT NOT NULL,
    entity_type TEXT NOT NULL
);
"""

def init_db() -> None:
    try:
        with connect() as cur:
            cur.execute(SCHEMA)
            
            # Seed data para equipos principales
            seed_query = """
            INSERT INTO teams (name, country_id, entity_type) VALUES
            ('Arsenal', 'EN', 'Club'), ('Chelsea', 'EN', 'Club'), 
            ('Man City', 'EN', 'Club'), ('Liverpool', 'EN', 'Club'),
            ('Real Madrid', 'ES', 'Club'), ('Barcelona', 'ES', 'Club'), 
            ('Atletico Madrid', 'ES', 'Club'), ('Sevilla', 'ES', 'Club'), ('Getafe', 'ES', 'Club'),
            ('Bayern Munich', 'DE', 'Club'), ('Dortmund', 'DE', 'Club'), 
            ('Leverkusen', 'DE', 'Club'), ('RB Leipzig', 'DE', 'Club'),
            ('Inter', 'IT', 'Club'), ('Juventus', 'IT', 'Club'), 
            ('Napoli', 'IT', 'Club'), ('Milan', 'IT', 'Club'),
            ('Paris SG', 'FR', 'Club'), ('Marseille', 'FR', 'Club'), 
            ('Monaco', 'FR', 'Club'), ('Lille', 'FR', 'Club'),
            ('Argentina', 'AR', 'Selección'), ('France', 'FR', 'Selección'), 
            ('Spain', 'ES', 'Selección'), ('England', 'EN', 'Selección')
            ON CONFLICT (name) DO NOTHING;
            """
            cur.execute(seed_query)
    except Exception as exc:
        print(f"[db] PostgreSQL init falló. Asegúrate de que Postgres corra: {exc}")

@contextmanager
def connect():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
