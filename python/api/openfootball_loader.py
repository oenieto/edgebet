"""
Edgebet — loader alternativo vía openfootball (GitHub JSON).

football-data.co.uk está bloqueado desde varias redes (timeouts SSL).
openfootball/football.json vive en raw.githubusercontent.com y responde
en ~300ms con cobertura de las 5 ligas grandes temporadas 2024-25 y 2025-26.

Limitaciones vs football-data.co.uk:
  - No trae stats granulares (shots, SoT, corners) — se dejan en 0.
  - No trae cuotas Bet365 — se mantienen cuotas sintéticas.
  - Nombres de equipos incluyen sufijos ("FC", "CF", "(ESP)") — se normalizan.

El modelo ya entrenado no depende de los nombres (solo features numéricas),
así que ELO + forma funcionan end-to-end con esta fuente.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# Cache disco reutiliza el mismo directorio que fast_loader
_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_OF_BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"
_OF_HISTORY_TTL = 6 * 3600        # 6h — histórico de temporada actual se actualiza
_OF_NETWORK_TIMEOUT = 6

# slug → (country_code, division). openfootball usa códigos ISO.
_SLUG_TO_OF: dict[str, str] = {
    "premier-league": "en.1",
    "la-liga": "es.1",
    "bundesliga": "de.1",
    "serie-a": "it.1",
    "ligue-1": "fr.1",
    "liga-mx": "mx.1",
}

# Temporadas cubiertas: actual + una anterior (para tener suficiente histórico
# para cómputo de ELO antes del matchday). openfootball Liga MX solo tiene
# 2024-25 publicado hoy; la carga gracefully ignora 404 en 2025-26.
_SEASONS = ("2024-25", "2025-26")

_mem: dict[str, tuple[float, dict]] = {}


def _fetch_json(url: str, ttl: int) -> dict | None:
    now = time.time()
    mem = _mem.get(url)
    if mem and (now - mem[0]) < ttl:
        return mem[1]

    import hashlib
    cache_path = _CACHE_DIR / f"of_{hashlib.sha1(url.encode()).hexdigest()[:16]}.json"
    if cache_path.exists() and (now - cache_path.stat().st_mtime) < ttl:
        try:
            data = json.loads(cache_path.read_text())
            _mem[url] = (now, data)
            return data
        except Exception:
            pass

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=_OF_NETWORK_TIMEOUT) as resp:
            raw = resp.read()
        data = json.loads(raw)
        cache_path.write_bytes(raw)
        _mem[url] = (now, data)
        return data
    except Exception as exc:
        # Stale fallback
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text())
                _mem[url] = (now, data)
                return data
            except Exception:
                pass
        print(f"[openfootball] fallo fetch {url}: {exc}")
        return None


# Normalización de nombres: openfootball usa "Manchester United FC (ENG)",
# queremos formas cortas consistentes para display y lookup cross-liga.
_NAME_OVERRIDES: dict[str, str] = {
    # EPL
    "Manchester United FC": "Man United",
    "Manchester City FC": "Man City",
    "Tottenham Hotspur FC": "Tottenham",
    "Newcastle United FC": "Newcastle",
    "West Ham United FC": "West Ham",
    "Aston Villa FC": "Aston Villa",
    "Nottingham Forest FC": "Nott'm Forest",
    "Wolverhampton Wanderers FC": "Wolves",
    "AFC Bournemouth": "Bournemouth",
    "Brighton & Hove Albion FC": "Brighton",
    "Crystal Palace FC": "Crystal Palace",
    "Leicester City FC": "Leicester",
    "Ipswich Town FC": "Ipswich",
    "Southampton FC": "Southampton",
    "Sunderland AFC": "Sunderland",
    "Burnley FC": "Burnley",
    "Liverpool FC": "Liverpool",
    "Arsenal FC": "Arsenal",
    "Chelsea FC": "Chelsea",
    "Everton FC": "Everton",
    "Fulham FC": "Fulham",
    "Brentford FC": "Brentford",
    "Leeds United AFC": "Leeds",
    # LaLiga
    "FC Barcelona": "Barcelona",
    "Real Madrid CF": "Real Madrid",
    "Club Atlético de Madrid": "Atletico Madrid",
    "Athletic Club": "Ath Bilbao",
    "Real Sociedad de Fútbol": "Real Sociedad",
    "Villarreal CF": "Villarreal",
    "Real Betis Balompié": "Betis",
    "Sevilla FC": "Sevilla",
    "Valencia CF": "Valencia",
    "Girona FC": "Girona",
    "RC Celta de Vigo": "Celta",
    "Getafe CF": "Getafe",
    "Deportivo Alavés": "Alaves",
    "CA Osasuna": "Osasuna",
    "RCD Mallorca": "Mallorca",
    "Rayo Vallecano de Madrid": "Vallecano",
    "RCD Espanyol de Barcelona": "Espanyol",
    "Real Oviedo": "Oviedo",
    "Elche CF": "Elche",
    "Levante UD": "Levante",
    # Bundesliga
    "FC Bayern München": "Bayern Munich",
    "Borussia Dortmund": "Dortmund",
    "Bayer 04 Leverkusen": "Leverkusen",
    "RB Leipzig": "RB Leipzig",
    "Eintracht Frankfurt": "Frankfurt",
    "VfB Stuttgart": "Stuttgart",
    "Borussia Mönchengladbach": "M'gladbach",
    "1. FSV Mainz 05": "Mainz",
    "SV Werder Bremen": "Werder Bremen",
    "1. FC Heidenheim 1846": "Heidenheim",
    "FC Augsburg": "Augsburg",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    "SC Freiburg": "Freiburg",
    "VfL Wolfsburg": "Wolfsburg",
    "FC St. Pauli": "St Pauli",
    "1. FC Köln": "FC Koln",
    "Hamburger SV": "Hamburg",
    "1. FC Union Berlin": "Union Berlin",
    # Serie A
    "FC Internazionale Milano": "Inter",
    "AC Milan": "Milan",
    "Juventus FC": "Juventus",
    "SSC Napoli": "Napoli",
    "AS Roma": "Roma",
    "SS Lazio": "Lazio",
    "Atalanta BC": "Atalanta",
    "ACF Fiorentina": "Fiorentina",
    "Bologna FC 1909": "Bologna",
    "Torino FC": "Torino",
    "Udinese Calcio": "Udinese",
    "Genoa CFC": "Genoa",
    "Parma Calcio 1913": "Parma",
    "Cagliari Calcio": "Cagliari",
    "Como 1907": "Como",
    "Hellas Verona FC": "Verona",
    "Empoli FC": "Empoli",
    "Venezia FC": "Venezia",
    "US Lecce": "Lecce",
    "US Sassuolo Calcio": "Sassuolo",
    "AC Monza": "Monza",
    "Cremonese": "Cremonese",
    "US Cremonese": "Cremonese",
    "Pisa Sporting Club": "Pisa",
    # Ligue 1
    "Paris Saint-Germain FC": "Paris SG",
    "AS Monaco FC": "Monaco",
    "Olympique de Marseille": "Marseille",
    "Olympique Lyonnais": "Lyon",
    "LOSC Lille": "Lille",
    "Lille OSC": "Lille",
    "OGC Nice": "Nice",
    "Stade Rennais FC 1901": "Rennes",
    "RC Lens": "Lens",
    "FC Nantes": "Nantes",
    "Stade Brestois 29": "Brest",
    "RC Strasbourg Alsace": "Strasbourg",
    "FC Lorient": "Lorient",
    "Le Havre AC": "Le Havre",
    "Toulouse FC": "Toulouse",
    "AJ Auxerre": "Auxerre",
    "AS Saint-Étienne": "St Etienne",
    "Angers SCO": "Angers",
    "Stade de Reims": "Reims",
    "Montpellier HSC": "Montpellier",
    "FC Metz": "Metz",
    "Paris FC": "Paris FC",
    # Liga MX
    "CF América": "America",
    "Club América": "America",
    "Cruz Azul": "Cruz Azul",
    "Deportivo Guadalajara": "Guadalajara",
    "CF Monterrey": "Monterrey",
    "CF Pachuca": "Pachuca",
    "Club León": "Leon",
    "UANL Tigres": "Tigres UANL",
    "Pumas UNAM": "Pumas UNAM",
    "Club Necaxa": "Necaxa",
    "Santos Laguna": "Santos Laguna",
    "Atlas Guadalajara": "Atlas",
    "Atlético San Luis": "Atletico San Luis",
    "Deportivo Toluca": "Toluca",
    "Club Tijuana": "Tijuana",
    "Mazatlán FC": "Mazatlan",
    "Puebla FC": "Puebla",
    "FC Juárez": "Juarez",
    "Gallos Blancos": "Queretaro",
}


def _normalize_team(raw: str) -> str:
    if not raw:
        return raw
    # Quitar sufijo " (XXX)" de país
    import re
    name = re.sub(r"\s*\([A-Z]{3}\)\s*$", "", raw).strip()
    if name in _NAME_OVERRIDES:
        return _NAME_OVERRIDES[name]
    # Heurística genérica: quitar sufijos club comunes al final
    for suf in (" FC", " CF", " AFC", " SC", " AC", " CFC"):
        if name.endswith(suf):
            name = name[: -len(suf)]
            break
    return name


def _match_to_row(m: dict) -> dict | None:
    """Convierte un match de openfootball al shape del loader CSV."""
    date_str = m.get("date")
    home = _normalize_team(m.get("team1", ""))
    away = _normalize_team(m.get("team2", ""))
    if not (date_str and home and away):
        return None

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

    row: dict = {
        "Date": date_obj.strftime("%d/%m/%Y"),
        "DateObj": date_obj,
        "Time": m.get("time", ""),
        "HomeTeam": home,
        "AwayTeam": away,
    }

    score_val = m.get("score")
    score = None
    if isinstance(score_val, dict):
        score = score_val.get("ft")
    elif isinstance(score_val, list):
        score = score_val

    if isinstance(score, list) and len(score) == 2 and all(s is not None for s in score):
        fthg, ftag = int(score[0]), int(score[1])
        row["FTHG"] = fthg
        row["FTAG"] = ftag
        if fthg > ftag:
            row["FTR"] = "H"
        elif fthg < ftag:
            row["FTR"] = "A"
        else:
            row["FTR"] = "D"
    # openfootball no trae stats granulares — quedan como strings vacíos
    for k in ("HS", "AS", "HST", "AST", "HC", "AC", "HF", "AF",
             "B365H", "B365D", "B365A"):
        row.setdefault(k, "")
    return row


def load_history_of(slug: str) -> list[dict]:
    """Partidos jugados (con score final) de las temporadas cubiertas."""
    code = _SLUG_TO_OF.get(slug)
    if not code:
        return []

    rows: list[dict] = []
    for season in _SEASONS:
        url = f"{_OF_BASE}/{season}/{code}.json"
        data = _fetch_json(url, _OF_HISTORY_TTL)
        if not data:
            continue
        for m in data.get("matches", []):
            row = _match_to_row(m)
            if row and row.get("FTR"):
                rows.append(row)

    rows.sort(key=lambda r: r["DateObj"])
    return rows


def _fixture_db_tuple(slug: str, row: dict, finished: bool) -> tuple | None:
    """Convierte una fila del loader al tuple que upserta en la tabla `fixtures`.

    external_id es determinista (of:<slug>:<fecha>:<home>_vs_<away>) para que el
    upsert sea idempotente: el mismo partido siempre apunta a la misma fila.
    """
    date_obj = row.get("DateObj")
    home = row.get("HomeTeam")
    away = row.get("AwayTeam")
    if not (isinstance(date_obj, datetime) and home and away):
        return None

    date_str = date_obj.strftime("%Y-%m-%d")
    time_str = (row.get("Time") or "").strip()
    kickoff = f"{date_str} {time_str}".strip()
    external_id = f"of:{slug}:{date_str}:{home}_vs_{away}".lower()
    status = "finished" if finished else "scheduled"
    home_score = int(row["FTHG"]) if finished and row.get("FTHG") != "" and row.get("FTHG") is not None else None
    away_score = int(row["FTAG"]) if finished and row.get("FTAG") != "" and row.get("FTAG") is not None else None
    return (external_id, slug, home, away, kickoff, status, home_score, away_score)


def upsert_fixtures(slugs: list[str] | None = None) -> int:
    """Persiste fixtures (jugados + próximos) en la tabla `fixtures`.

    Idempotente vía `external_id` como clave de conflicto: corre cuantas veces
    haga falta sin duplicar. Los partidos terminados quedan con status='finished'
    y marcador, que es lo que `settle_pending_picks()` necesita para liquidar.

    Devuelve el número de filas upserted.
    """
    # Import diferido: db importa schema, evitamos costo de import al cargar el módulo.
    from api.db import connect

    slugs = slugs or list(_SLUG_TO_OF.keys())
    rows: list[tuple] = []
    for slug in slugs:
        for r in load_history_of(slug):
            t = _fixture_db_tuple(slug, r, finished=True)
            if t:
                rows.append(t)
        for r in load_fixtures_of([slug]):
            t = _fixture_db_tuple(slug, r, finished=False)
            if t:
                rows.append(t)

    if not rows:
        return 0

    upserted = 0
    try:
        with connect() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO fixtures
                        (external_id, league_slug, home_team, away_team, kickoff,
                         status, home_score, away_score, last_synced)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (external_id) DO UPDATE SET
                        status=excluded.status,
                        home_score=excluded.home_score,
                        away_score=excluded.away_score,
                        kickoff=excluded.kickoff,
                        last_synced=CURRENT_TIMESTAMP
                    """,
                    row,
                )
                upserted += 1
    except Exception as exc:
        print(f"[openfootball] upsert_fixtures falló: {exc}")
        return upserted

    print(f"[openfootball] upsert_fixtures: {upserted} fixtures persistidos")
    return upserted


def load_fixtures_of(slugs: list[str]) -> list[dict]:
    """Próximos partidos (sin score) por liga."""
    fixtures: list[dict] = []
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    for slug in slugs:
        code = _SLUG_TO_OF.get(slug)
        if not code:
            continue
        # Solo la temporada actual tiene próximos partidos
        url = f"{_OF_BASE}/2025-26/{code}.json"
        data = _fetch_json(url, 900)  # 15 min para fixtures
        if not data:
            continue
        for m in data.get("matches", []):
            score_val = m.get("score")
            score = None
            if isinstance(score_val, dict):
                score = score_val.get("ft")
            elif isinstance(score_val, list):
                score = score_val

            if score is not None:
                continue
            if m.get("date", "") < today_str:
                continue
            row = _match_to_row(m)
            if row:
                row["leagueSlug"] = slug
                fixtures.append(row)
    fixtures.sort(key=lambda r: (r["DateObj"], r.get("Time", "")))
    return fixtures
