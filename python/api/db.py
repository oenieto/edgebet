"""
Database setup para Edgebet with PostgreSQL primary and SQLite fallback.
Schema canónico vive en api/schema.py — este módulo solo gestiona conexión,
migración (idempotente) y seeds.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager

from api.schema import SCHEMA_PG, RANK_SEEDS, ACHIEVEMENT_SEEDS

# Try to use psycopg2 if available
try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://edgebet:edgebet@localhost:5432/edgebet"
)
USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() == "true" or not HAS_PSYCOPG2

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "edgebet.db")


def _pg_to_sqlite(schema: str) -> str:
    """Conversión sintáctica de Postgres → SQLite. Conservadora a propósito —
    solo toca lo que ambos no soportan idénticamente."""
    return (
        schema
        .replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
        .replace("TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT CURRENT_TIMESTAMP")
        .replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT CURRENT_TIMESTAMP")
        .replace("TIMESTAMP", "DATETIME")
        .replace("REAL", "FLOAT")
    )


SCHEMA_SQLITE = _pg_to_sqlite(SCHEMA_PG)


# ============================================================
# MIGRACIÓN INCREMENTAL — añade columnas a tablas viejas que no
# tienen las nuevas (role, market, xp_awarded, etc.). SQLite limita
# ALTER TABLE a ADD COLUMN; suficiente para todos los nuevos campos.
# ============================================================
# (tabla, columna, declaración). Compartido entre SQLite y Postgres: la
# declaración usa tipos que ambos aceptan (TEXT/INTEGER). DATETIME se traduce a
# TIMESTAMP para Postgres en _ensure_columns_pg.
_INCREMENTAL_COLUMNS = [
    ("users", "role", "TEXT NOT NULL DEFAULT 'user'"),
    ("users", "avatar_url", "TEXT"),
    ("user_bets", "market", "TEXT DEFAULT 'ML'"),
    ("user_bets", "xp_awarded", "INTEGER DEFAULT 0"),
    ("user_bets", "bookmaker", "TEXT"),
    ("user_bets", "settled_at", "DATETIME"),
    # Soporte de torneos internacionales en fixtures (overhaul Phase 1.2 / 3.1).
    ("fixtures", "tournament_phase", "TEXT"),
    ("fixtures", "match_group", "TEXT"),
    ("fixtures", "round_number", "INTEGER"),
]

# Alias retro-compatible.
_INCREMENTAL_COLUMNS_SQLITE = _INCREMENTAL_COLUMNS


def _ensure_columns_sqlite(conn) -> None:
    cur = conn.cursor()
    for table, col, decl in _INCREMENTAL_COLUMNS:
        try:
            cur.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in cur.fetchall()}
            if col not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
                print(f"[db] +column {table}.{col}")
        except sqlite3.Error as exc:
            print(f"[db] no pude agregar {table}.{col}: {exc}")


def _ensure_columns_pg(cur) -> None:
    """Migración incremental idempotente para Postgres.

    Postgres soporta `ADD COLUMN IF NOT EXISTS`, así que es seguro correrlo en
    cada cold-start. DATETIME se mapea a TIMESTAMP.
    """
    for table, col, decl in _INCREMENTAL_COLUMNS:
        pg_decl = decl.replace("DATETIME", "TIMESTAMP")
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {pg_decl}")
        except Exception as exc:
            print(f"[db] (pg) no pude agregar {table}.{col}: {exc}")


def init_db() -> None:
    global USE_SQLITE
    try:
        if not USE_SQLITE:
            try:
                with connect_pg() as cur:
                    cur.execute(SCHEMA_PG)
                    _ensure_columns_pg(cur)
                    seed_teams(cur)
                    seed_ranks_pg(cur)
                    seed_achievements_pg(cur)
                    print("[db] PostgreSQL inicializado correctamente.")
                    return
            except Exception as e:
                print(f"[db] PostgreSQL falló, usando SQLite como fallback: {e}")
                USE_SQLITE = True

        # Fallback a SQLite
        os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
        with connect_sqlite() as conn:
            conn.executescript(SCHEMA_SQLITE)
            _ensure_columns_sqlite(conn)
            seed_teams_sqlite(conn)
            seed_ranks_sqlite(conn)
            seed_achievements_sqlite(conn)
            print(f"[db] SQLite inicializado correctamente en {SQLITE_DB_PATH}")

    except Exception as exc:
        print(f"[db] Error crítico inicializando base de datos: {exc}")

def seed_teams(cur) -> None:
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

def seed_teams_sqlite(conn) -> None:
    teams = [
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
    ]
    cur = conn.cursor()
    for t in teams:
        cur.execute("INSERT OR IGNORE INTO teams (name, country_id, entity_type) VALUES (?, ?, ?)", t)
    conn.commit()


# ============================================================
# SEEDS — RANKS y ACHIEVEMENTS
# ============================================================
_RANK_INSERT_SQL_PG = """
INSERT INTO ranks (code, name, tier_index, min_xp, color_hex, icon, description)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    tier_index = EXCLUDED.tier_index,
    min_xp = EXCLUDED.min_xp,
    color_hex = EXCLUDED.color_hex,
    icon = EXCLUDED.icon,
    description = EXCLUDED.description
"""

_ACHIEVEMENT_INSERT_SQL_PG = """
INSERT INTO achievements (code, name, description, category, xp_reward, icon, rarity)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    xp_reward = EXCLUDED.xp_reward,
    icon = EXCLUDED.icon,
    rarity = EXCLUDED.rarity
"""


def seed_ranks_pg(cur) -> None:
    for r in RANK_SEEDS:
        cur.execute(_RANK_INSERT_SQL_PG, (
            r["code"], r["name"], r["tier_index"], r["min_xp"],
            r["color_hex"], r["icon"], r["description"],
        ))


def seed_achievements_pg(cur) -> None:
    for a in ACHIEVEMENT_SEEDS:
        cur.execute(_ACHIEVEMENT_INSERT_SQL_PG, (
            a["code"], a["name"], a["description"], a["category"],
            a["xp_reward"], a["icon"], a["rarity"],
        ))


def seed_ranks_sqlite(conn) -> None:
    """Upsert manual: SQLite no tiene sintaxis idéntica para ON CONFLICT
    sobre múltiples columnas, pero como `code` es UNIQUE basta INSERT OR
    REPLACE manteniendo los seeds como source of truth."""
    cur = conn.cursor()
    for r in RANK_SEEDS:
        cur.execute("""
            INSERT INTO ranks (code, name, tier_index, min_xp, color_hex, icon, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name,
                tier_index=excluded.tier_index,
                min_xp=excluded.min_xp,
                color_hex=excluded.color_hex,
                icon=excluded.icon,
                description=excluded.description
        """, (
            r["code"], r["name"], r["tier_index"], r["min_xp"],
            r["color_hex"], r["icon"], r["description"],
        ))
    conn.commit()


def seed_achievements_sqlite(conn) -> None:
    cur = conn.cursor()
    for a in ACHIEVEMENT_SEEDS:
        cur.execute("""
            INSERT INTO achievements (code, name, description, category, xp_reward, icon, rarity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                category=excluded.category,
                xp_reward=excluded.xp_reward,
                icon=excluded.icon,
                rarity=excluded.rarity
        """, (
            a["code"], a["name"], a["description"], a["category"],
            a["xp_reward"], a["icon"], a["rarity"],
        ))
    conn.commit()

class _SqliteCursorProxy:
    """
    Proxy alrededor de sqlite3.Cursor que:
      - Traduce placeholders psycopg2 (%s) → SQLite (?).
      - Simula `RETURNING id` (no soportado en SQLite < 3.35) capturando
        lastrowid y devolviéndolo en el siguiente fetchone().
      - Respeta `IntegrityError` para que la lógica de auth lo capture igual.

    Antes era monkey-patch directo sobre el cursor, pero Python 3.14 hizo
    los atributos de sqlite3.Cursor read-only y eso rompía login/register
    con AttributeError. Con proxy delegamos sin tocar la instancia real.
    """

    def __init__(self, cursor):
        self._cursor = cursor
        self._returning_id_pending: int | None = None

    def execute(self, query: str, params=None):
        if params is not None and "%s" in query:
            query = query.replace("%s", "?")
        returning_id = False
        if "RETURNING id" in query:
            query = query.replace("RETURNING id", "")
            returning_id = True
        if "ON CONFLICT" in query and "DO NOTHING" in query:
            # Postgres-style UPSERT — sqlite usa INSERT OR IGNORE
            query = (
                query.replace("ON CONFLICT (name) DO NOTHING", "")
                     .replace("INSERT INTO", "INSERT OR IGNORE INTO", 1)
            )
        result = self._cursor.execute(query, params or [])
        if returning_id:
            self._returning_id_pending = self._cursor.lastrowid
        return result

    def executemany(self, query, seq_of_params):
        if "%s" in query:
            query = query.replace("%s", "?")
        return self._cursor.executemany(query, seq_of_params)

    def fetchone(self):
        if self._returning_id_pending is not None:
            val = {"id": self._returning_id_pending}
            self._returning_id_pending = None
            return val
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        return self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)


@contextmanager
def connect():
    if USE_SQLITE:
        with connect_sqlite() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            yield _SqliteCursorProxy(cursor)
            conn.commit()
    else:
        with connect_pg() as cur:
            yield cur

@contextmanager
def connect_pg():
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

@contextmanager
def connect_sqlite():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
