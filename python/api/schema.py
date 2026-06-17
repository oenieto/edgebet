"""
Edgebet — definición canónica del schema.

Convención:
  - Postgres como source of truth (SCHEMA_PG).
  - SQLite se deriva de PG con sustituciones simples (ver db.py:_pg_to_sqlite).
  - Toda tabla nueva DEBE ser CREATE TABLE IF NOT EXISTS para que migraciones
    sean idempotentes en cold-start.
  - Constraints suaves: si la versión vieja de la tabla existe sin la columna
    nueva, evitar romperla — preferir tabla nueva o columna NULL-able.
"""
from __future__ import annotations


SCHEMA_PG = """
-- ============================================================
-- USUARIOS Y AUTH
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    role TEXT NOT NULL DEFAULT 'user',
    avatar_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    onboarding_done BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);

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

-- ============================================================
-- BANKROLL & APUESTAS DEL USUARIO
-- ============================================================
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
    market TEXT DEFAULT 'ML',           -- ML | OU | DC
    stake REAL NOT NULL,
    odds REAL,
    result TEXT,                         -- 'pending' | 'win' | 'loss' | 'void'
    pnl REAL,
    xp_awarded INTEGER DEFAULT 0,        -- XP otorgado al settle (idempotente)
    bookmaker TEXT,                      -- 'bet365' | 'pinnacle' | 'manual'
    bet_date TEXT NOT NULL,
    settled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_bets_user ON user_bets(user_id);
CREATE INDEX IF NOT EXISTS idx_user_bets_result ON user_bets(result);

CREATE TABLE IF NOT EXISTS user_alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    alert_type TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    threshold_pct REAL,
    triggered_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- DOMINIO DE FÚTBOL
-- ============================================================
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    country_id TEXT NOT NULL,
    entity_type TEXT NOT NULL
);

-- Fixtures persistidos: replica el cache en memoria pero con TTL controlado
-- y posibilidad de joinear con stats / odds / events.
CREATE TABLE IF NOT EXISTS fixtures (
    id SERIAL PRIMARY KEY,
    external_id TEXT UNIQUE,             -- id en provider externo (the-odds-api / api-football)
    league_slug TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    kickoff TIMESTAMP NOT NULL,
    venue TEXT,
    status TEXT DEFAULT 'scheduled',     -- scheduled | live | ht | finished | postponed
    minute INTEGER,                       -- si live
    home_score INTEGER,
    away_score INTEGER,
    -- Torneos internacionales (FIFA World Cup 2026 y futuros).
    tournament_phase TEXT,                -- group_stage | round_of_32 | round_of_16 | quarter_final | semi_final | third_place | final
    match_group TEXT,                     -- 'A'..'L' en fase de grupos; NULL en eliminatorias
    round_number INTEGER,                 -- jornada dentro del grupo o nº de ronda eliminatoria
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fixtures_kickoff ON fixtures(kickoff);
CREATE INDEX IF NOT EXISTS idx_fixtures_league ON fixtures(league_slug);
CREATE INDEX IF NOT EXISTS idx_fixtures_status ON fixtures(status);

-- Stats Sofascore-style por partido (snapshot post-match o live)
CREATE TABLE IF NOT EXISTS match_stats (
    id SERIAL PRIMARY KEY,
    fixture_id INTEGER REFERENCES fixtures(id) ON DELETE CASCADE,
    side TEXT NOT NULL,                  -- 'home' | 'away'
    possession_pct REAL,
    shots INTEGER,
    shots_on_target INTEGER,
    corners INTEGER,
    fouls INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,
    offsides INTEGER,
    pass_accuracy_pct REAL,
    expected_goals REAL,                  -- xG real del provider
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_match_stats_fixture ON match_stats(fixture_id);

-- Eventos del partido: gol, tarjeta, sustitución, penalti, var
CREATE TABLE IF NOT EXISTS match_events (
    id SERIAL PRIMARY KEY,
    fixture_id INTEGER REFERENCES fixtures(id) ON DELETE CASCADE,
    minute INTEGER NOT NULL,
    side TEXT NOT NULL,
    event_type TEXT NOT NULL,            -- goal | yellow | red | sub_in | sub_out | penalty | var | own_goal
    player_name TEXT,
    detail TEXT,                          -- e.g. "asistencia: X" o motivo de tarjeta
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_match_events_fixture ON match_events(fixture_id);

-- Lineups: alineación + formación
CREATE TABLE IF NOT EXISTS match_lineups (
    id SERIAL PRIMARY KEY,
    fixture_id INTEGER REFERENCES fixtures(id) ON DELETE CASCADE,
    side TEXT NOT NULL,
    formation TEXT,                       -- '4-3-3', '4-2-3-1' etc.
    starting_xi TEXT,                     -- JSON array de {name, position, jersey}
    bench TEXT,                           -- JSON array igual
    coach TEXT,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_match_lineups_fixture ON match_lineups(fixture_id);

-- Cache pre-computado de H2H entre dos equipos (acelera el endpoint /picks/{id}/stats)
CREATE TABLE IF NOT EXISTS h2h_cache (
    id SERIAL PRIMARY KEY,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    last_n_matches TEXT,                  -- JSON array de matches H2H
    home_wins INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    away_wins INTEGER DEFAULT 0,
    avg_total_goals REAL,
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(home_team, away_team)
);

-- ============================================================
-- ODDS — historial e instantáneas de casas reales
-- ============================================================
CREATE TABLE IF NOT EXISTS odds_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_id TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    market TEXT NOT NULL,
    odds_value REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_odds_history_event_id ON odds_history(event_id);
CREATE INDEX IF NOT EXISTS idx_odds_history_timestamp ON odds_history(timestamp);
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id SERIAL PRIMARY KEY,
    fixture_id INTEGER REFERENCES fixtures(id) ON DELETE CASCADE,
    bookmaker TEXT NOT NULL,             -- 'bet365' | 'pinnacle' | 'unibet' | ...
    market TEXT NOT NULL,                -- 'h2h' | 'totals' | 'spreads'
    home_odds REAL,
    draw_odds REAL,
    away_odds REAL,
    over_2_5_odds REAL,
    under_2_5_odds REAL,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_odds_fixture ON odds_snapshots(fixture_id);
CREATE INDEX IF NOT EXISTS idx_odds_captured ON odds_snapshots(captured_at);

-- ============================================================
-- RANKS, XP, ACHIEVEMENTS
-- ============================================================
-- Tabla maestra de rangos: definición canónica.
CREATE TABLE IF NOT EXISTS ranks (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,           -- 'rookie', 'analyst', etc.
    name TEXT NOT NULL,
    tier_index INTEGER NOT NULL,         -- 0 = entry, mayor = mejor
    min_xp INTEGER NOT NULL,             -- XP requerido para ingresar
    color_hex TEXT,                      -- color del badge
    icon TEXT,                            -- nombre de icono lucide-react
    description TEXT
);

-- Estado actual del usuario en el sistema de rangos.
CREATE TABLE IF NOT EXISTS user_ranks (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    current_rank_code TEXT NOT NULL DEFAULT 'rookie',
    total_xp INTEGER NOT NULL DEFAULT 0,
    bets_won INTEGER NOT NULL DEFAULT 0,
    bets_lost INTEGER NOT NULL DEFAULT 0,
    longshot_wins INTEGER NOT NULL DEFAULT 0,    -- wins con odds >= 2.50
    biggest_win_odds REAL DEFAULT 0,
    streak_current INTEGER DEFAULT 0,             -- racha actual de wins consecutivos
    streak_best INTEGER DEFAULT 0,
    last_evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Log audit de subidas/bajadas de rango.
CREATE TABLE IF NOT EXISTS rank_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    from_rank TEXT,
    to_rank TEXT NOT NULL,
    direction TEXT NOT NULL,             -- 'up' | 'down'
    total_xp_at_event INTEGER NOT NULL,
    triggered_by_bet_id INTEGER,         -- nullable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rank_history_user ON rank_history(user_id);

-- Definición de logros (achievements).
CREATE TABLE IF NOT EXISTS achievements (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,              -- 'volume' | 'odds' | 'streak' | 'roi' | 'social'
    xp_reward INTEGER NOT NULL DEFAULT 0,
    icon TEXT,
    rarity TEXT DEFAULT 'common'         -- 'common' | 'rare' | 'epic' | 'legendary'
);

-- Logros desbloqueados por usuario.
CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    achievement_code TEXT NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, achievement_code)
);

CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);

-- ============================================================
-- LEADERBOARDS y referidos (esqueleto)
-- ============================================================
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    referred_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    converted_at TIMESTAMP,
    bonus_xp INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(referrer_id, referred_id)
);

-- ============================================================
-- SETTLEMENT LOG
-- ============================================================
CREATE TABLE IF NOT EXISTS settlement_log (
    id SERIAL PRIMARY KEY,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    picks_settled INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    accuracy_pct REAL,
    notes TEXT
);

-- ============================================================
-- PICKS PERSISTIDOS
-- ============================================================
CREATE TABLE IF NOT EXISTS picks (
    id TEXT PRIMARY KEY,
    match TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_logo TEXT,
    away_logo TEXT,
    league TEXT NOT NULL,
    league_logo TEXT,
    league_slug TEXT,
    market TEXT DEFAULT 'ML',
    kickoff TIMESTAMP NOT NULL,
    prediction TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    ml_prob_home REAL NOT NULL,
    ml_prob_draw REAL NOT NULL,
    ml_prob_away REAL NOT NULL,
    poly_prob_home REAL,
    poly_prob_draw REAL,
    poly_prob_away REAL,
    bk_prob_home REAL NOT NULL,
    bk_prob_draw REAL NOT NULL,
    bk_prob_away REAL NOT NULL,
    blended_prob_home REAL,
    blended_prob_draw REAL,
    blended_prob_away REAL,
    ai_reasoning TEXT,
    suggested_stake REAL NOT NULL,
    status TEXT NOT NULL,
    odds REAL,
    edge_pp REAL,
    ev_pct REAL,
    sources_agree BOOLEAN,
    market_verified BOOLEAN,
    markets_json TEXT,
    poly_meta_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_picks_kickoff ON picks(kickoff);
CREATE INDEX IF NOT EXISTS idx_picks_league ON picks(league_slug);

-- Sistema de registro ML/analítica: salida cruda del pipeline por fixture
-- (probabilidades, EV por resultado, Kelly, narrativa, método). Distinta de
-- `picks` (formato de display para el frontend); se escribe en paralelo y
-- sirve para backtesting/evaluación del modelo. NOW() no existe en SQLite, por
-- eso CURRENT_TIMESTAMP.
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    fixture_id INTEGER REFERENCES fixtures(id) ON DELETE SET NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    match_date DATE,
    league TEXT,
    home_team TEXT,
    away_team TEXT,
    predicted_prob_home REAL,
    predicted_prob_draw REAL,
    predicted_prob_away REAL,
    ev_home REAL,
    ev_draw REAL,
    ev_away REAL,
    recommended_bet TEXT,
    kelly_stake REAL,
    narrative TEXT,
    method TEXT DEFAULT 'ensemble',
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_match_date ON predictions(match_date);
CREATE INDEX IF NOT EXISTS idx_predictions_fixture ON predictions(fixture_id);

-- ============================================================
-- BANKROLL — capital, movimientos y curva de equity por usuario
-- ============================================================
-- Nota: NOW() no existe en SQLite; usamos CURRENT_TIMESTAMP. FLOAT→REAL para
-- mantener la convención del schema (db.py traduce REAL→FLOAT en SQLite).
CREATE TABLE IF NOT EXISTS bankroll (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    initial_capital REAL NOT NULL DEFAULT 1000.0,
    current_balance REAL NOT NULL DEFAULT 1000.0,
    currency        TEXT NOT NULL DEFAULT 'USD',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bankroll_transactions (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type          TEXT NOT NULL,   -- deposit | withdrawal | bet_placed | bet_won | bet_lost | bet_void | adjustment
    amount        REAL NOT NULL,   -- positivo = crédito, negativo = débito
    balance_after REAL NOT NULL,
    reference_id  INTEGER,         -- FK lógica a user_bets.id cuando type = bet_*
    note          TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bankroll_tx_user ON bankroll_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_bankroll_tx_created ON bankroll_transactions(created_at);

CREATE TABLE IF NOT EXISTS bankroll_equity_log (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    balance       REAL NOT NULL,
    UNIQUE(user_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_bankroll_equity_user ON bankroll_equity_log(user_id);

-- ============================================================
-- PLAYER STATS (for player props)
-- ============================================================
CREATE TABLE IF NOT EXISTS player_stats (
    id SERIAL PRIMARY KEY,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    league_slug TEXT,
    season TEXT,
    appearances INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    shots_per_90 REAL DEFAULT 0,
    sot_per_90 REAL DEFAULT 0,
    cards_per_90 REAL DEFAULT 0,
    passes_per_90 REAL DEFAULT 0,
    xg_per_90 REAL DEFAULT 0,
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_name, team, season)
);

CREATE INDEX IF NOT EXISTS idx_player_stats_team ON player_stats(team);
CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_stats(player_name);
"""


# Seeds — tabla de rangos canónicos. Calibrada para que un usuario activo
# cruce ~2 rangos en su primer mes de uso intensivo (≈30 picks/mes con
# 55% accuracy y odds promedio 1.85 → ~600 XP/mes).
RANK_SEEDS: list[dict] = [
    {"code": "rookie",       "name": "Apostador",      "tier_index": 0, "min_xp": 0,     "color_hex": "#94a3b8", "icon": "Sparkles",  "description": "Primeros pasos en el edge."},
    {"code": "analyst",      "name": "Analista",       "tier_index": 1, "min_xp": 100,   "color_hex": "#60a5fa", "icon": "Activity",  "description": "Sigues los datos, no la corazonada."},
    {"code": "strategist",   "name": "Estratega",      "tier_index": 2, "min_xp": 300,   "color_hex": "#34d399", "icon": "Compass",   "description": "Diversificas y gestionas bankroll."},
    {"code": "quant",        "name": "Cuantitativo",   "tier_index": 3, "min_xp": 700,   "color_hex": "#a78bfa", "icon": "BarChart3", "description": "Lees divergencias antes que el mercado."},
    {"code": "sharpshooter", "name": "Sharpshooter",   "tier_index": 4, "min_xp": 1500,  "color_hex": "#f59e0b", "icon": "Target",    "description": "ROI sostenido, pierdes poco."},
    {"code": "edge_hunter",  "name": "Edge Hunter",    "tier_index": 5, "min_xp": 3000,  "color_hex": "#f97316", "icon": "Crosshair", "description": "El mercado te debe varios."},
    {"code": "master",       "name": "Master Quant",   "tier_index": 6, "min_xp": 6000,  "color_hex": "#ef4444", "icon": "Crown",     "description": "Consistencia de élite."},
    {"code": "legend",       "name": "Legend",         "tier_index": 7, "min_xp": 12000, "color_hex": "#fbbf24", "icon": "Trophy",    "description": "Top 1% all-time."},
]


# Seeds — logros base. xp_reward se acumula al desbloquear.
ACHIEVEMENT_SEEDS: list[dict] = [
    # Volumen
    {"code": "first_bet",       "name": "Primer pick",         "description": "Registra tu primera apuesta.",                         "category": "volume", "xp_reward": 25,  "icon": "Sparkles",  "rarity": "common"},
    {"code": "ten_bets",        "name": "Decena",              "description": "10 apuestas registradas.",                             "category": "volume", "xp_reward": 50,  "icon": "Activity",  "rarity": "common"},
    {"code": "fifty_bets",      "name": "Cincuentón",          "description": "50 apuestas registradas.",                             "category": "volume", "xp_reward": 150, "icon": "Activity",  "rarity": "rare"},
    {"code": "hundred_bets",    "name": "Centurión",           "description": "100 apuestas registradas.",                            "category": "volume", "xp_reward": 300, "icon": "Trophy",    "rarity": "epic"},
    # Odds (longshot)
    {"code": "longshot_2",      "name": "Outsider",            "description": "Win con cuota ≥ 2.50.",                                "category": "odds",   "xp_reward": 75,  "icon": "Zap",       "rarity": "rare"},
    {"code": "longshot_3",      "name": "Odds 3+",             "description": "Win con cuota ≥ 3.00.",                                "category": "odds",   "xp_reward": 150, "icon": "Flame",     "rarity": "epic"},
    {"code": "longshot_5",      "name": "Cazaedges",           "description": "Win con cuota ≥ 5.00.",                                "category": "odds",   "xp_reward": 350, "icon": "Crosshair", "rarity": "legendary"},
    # Rachas
    {"code": "streak_3",        "name": "Tripleta",            "description": "3 wins consecutivos.",                                 "category": "streak", "xp_reward": 60,  "icon": "TrendingUp","rarity": "common"},
    {"code": "streak_5",        "name": "En racha",            "description": "5 wins consecutivos.",                                 "category": "streak", "xp_reward": 150, "icon": "Flame",     "rarity": "rare"},
    {"code": "streak_10",       "name": "Inquebrantable",      "description": "10 wins consecutivos.",                                "category": "streak", "xp_reward": 500, "icon": "Crown",     "rarity": "legendary"},
    # Social
    {"code": "first_referral",  "name": "Embajador",           "description": "Invita a un amigo que se registre.",                   "category": "social", "xp_reward": 100, "icon": "Users",     "rarity": "common"},
]
