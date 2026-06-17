"""
Edgebet — loader de histórico de selecciones nacionales (últimos ~5 años).

Alimenta al PoissonPredictor con partidos reales para que las probabilidades
del Mundial pasen de ELO puro a Poisson basado en goles reales.

Fuentes (ambas gratuitas):
  A) football-data.co.uk — CSVs de partidos. Históricamente su cobertura es de
     ligas de clubes; los CSV de selecciones NO están disponibles en una ruta
     estable hoy (la página /internationals.php responde 300 sin enlaces .csv).
     Se intenta best-effort y, si no hay datos, se omite con aviso.
  B) football-data.org REST API — requiere `FOOTBALL_DATA_API_KEY` (free tier).
     Sin la key responde 403 en TODOS los endpoints (incluido WC). Si falta la
     key, se omite con aviso — NUNCA crashea.

Regla dura del proyecto: si ninguna fuente devuelve datos, NO se inventa nada.
Se escribe un CSV vacío (solo cabecera) y el predictor cae a ELO honestamente.
"""
from __future__ import annotations

import csv
import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger("edgebet.natloader")

DATA_DIR = Path(__file__).resolve().parent
HISTORY_CSV = DATA_DIR / "national_teams_history.csv"

CSV_COLUMNS = ["date", "home_team", "away_team", "home_goals", "away_goals", "competition", "stage"]

MIN_DATE = "2019-01-01"
_REQUEST_TIMEOUT = 12

# ---------------------------------------------------------------------------
# Normalización de nombres → claves canónicas de world_cup.py
# ---------------------------------------------------------------------------
_NAME_CANON: dict[str, str] = {
    "united states": "USA",
    "united states of america": "USA",
    "usa": "USA",
    "korea republic": "South Korea",
    "south korea": "South Korea",
    "republic of korea": "South Korea",
    "ir iran": "Iran",
    "iran": "Iran",
    "côte d'ivoire": "Ivory Coast",
    "cote d'ivoire": "Ivory Coast",
    "ivory coast": "Ivory Coast",
    "holland": "Netherlands",
    "netherlands": "Netherlands",
    "czech republic": "Czechia",
    "england": "England",
    "saudi arabia": "Saudi Arabia",
    "south africa": "South Africa",
    "new zealand": "New Zealand",
    "costa rica": "Costa Rica",
    "curaçao": "Curacao",
    "curacao": "Curacao",
}


def _canon(name: str) -> str:
    if not name:
        return name
    key = name.strip()
    return _NAME_CANON.get(key.lower(), key)


# ---------------------------------------------------------------------------
# SOURCE A — football-data.co.uk
# ---------------------------------------------------------------------------
# Rutas candidatas best-effort. football-data.co.uk no publica CSVs de
# selecciones en una ubicación estable hoy; si alguna existiera en el futuro,
# se parsea aquí. Cualquier fallo (300/404/red) se traga y devuelve [].
_FDCOUK_CANDIDATES = [
    "https://www.football-data.co.uk/new/internationals.csv",
    "https://www.football-data.co.uk/internationals.csv",
]


def _load_football_data_couk() -> list[dict]:
    rows: list[dict] = []
    for url in _FDCOUK_CANDIDATES:
        try:
            resp = requests.get(url, timeout=_REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        except requests.RequestException as exc:
            logger.warning("[natloader] A: red falló %s: %s", url, exc)
            continue
        ctype = resp.headers.get("Content-Type", "")
        if resp.status_code != 200 or "csv" not in ctype.lower() and not resp.text.lstrip().lower().startswith("date"):
            logger.info("[natloader] A: %s no es CSV utilizable (status=%s)", url, resp.status_code)
            continue
        try:
            reader = csv.DictReader(io.StringIO(resp.text))
            for r in reader:
                date = _parse_date(r.get("Date"))
                home, away = _canon(r.get("HomeTeam", "")), _canon(r.get("AwayTeam", ""))
                hg, ag = _to_int(r.get("FTHG")), _to_int(r.get("FTAG"))
                if not (date and home and away) or hg is None or ag is None:
                    continue
                rows.append({
                    "date": date, "home_team": home, "away_team": away,
                    "home_goals": hg, "away_goals": ag,
                    "competition": r.get("Comp") or r.get("League") or "International",
                    "stage": r.get("Stage") or "",
                })
        except Exception as exc:
            logger.warning("[natloader] A: parse falló %s: %s", url, exc)
    if rows:
        logger.info("[natloader] A: %d partidos desde football-data.co.uk", len(rows))
    else:
        logger.warning("[natloader] A: sin CSVs de selecciones disponibles — se omite.")
    return rows


# ---------------------------------------------------------------------------
# SOURCE B — football-data.org REST API
# ---------------------------------------------------------------------------
# Competiciones de SELECCIONES NACIONALES. CLI (Copa Libertadores) y CL/PL son
# de CLUBES: se excluyen a propósito porque mezclarían su línea base de goles con
# la de selecciones y sesgarían el modelo nacional. CA (Copa América) y WCQ no
# están en el free tier (403/404) — se omiten en caliente.
# NOTA free tier: football-data.org solo expone la temporada ACTUAL de cada
# competición; las históricas (2019–2023) devuelven 403. En la práctica esto da
# WC 2026 (en curso) + EURO 2024.
_FDORG_COMPETITIONS = ["WC", "EC", "CA", "WCQ"]
_FDORG_BASE = "https://api.football-data.org/v4/competitions"


def _load_football_data_org() -> list[dict]:
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        logger.warning(
            "[natloader] B: FOOTBALL_DATA_API_KEY ausente — se omite football-data.org "
            "(devuelve 403 sin key). Las selecciones caerán a ELO."
        )
        return []

    headers = {"X-Auth-Token": api_key}
    rows: list[dict] = []
    skipped: list[str] = []
    for comp in _FDORG_COMPETITIONS:
        url = f"{_FDORG_BASE}/{comp}/matches?status=FINISHED"
        try:
            resp = requests.get(url, headers=headers, timeout=_REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            skipped.append(f"{comp}(red:{exc})")
            continue
        if resp.status_code in (403, 404):
            skipped.append(f"{comp}({resp.status_code} no disponible en free tier)")
            continue
        if resp.status_code == 429:
            skipped.append(f"{comp}(429 rate-limit)")
            continue
        if resp.status_code != 200:
            skipped.append(f"{comp}({resp.status_code})")
            continue
        try:
            data = resp.json()
        except ValueError:
            skipped.append(f"{comp}(json)")
            continue

        comp_rows = 0
        for m in data.get("matches", []):
            if m.get("status") != "FINISHED":
                continue
            ft = (m.get("score") or {}).get("fullTime") or {}
            hg, ag = ft.get("home"), ft.get("away")
            if hg is None or ag is None:
                continue
            date = _parse_date(m.get("utcDate"))
            home = _canon((m.get("homeTeam") or {}).get("name", ""))
            away = _canon((m.get("awayTeam") or {}).get("name", ""))
            if not (date and home and away):
                continue
            rows.append({
                "date": date, "home_team": home, "away_team": away,
                "home_goals": int(hg), "away_goals": int(ag),
                "competition": comp, "stage": m.get("stage") or "",
            })
            comp_rows += 1
        logger.info("[natloader] B: %s → %d partidos", comp, comp_rows)

    if skipped:
        logger.warning("[natloader] B: competiciones omitidas: %s", ", ".join(skipped))
    logger.info("[natloader] B: %d partidos nacionales en total", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _to_int(v) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Merge + persistencia
# ---------------------------------------------------------------------------
def load_and_merge(write: bool = True) -> list[dict]:
    """Descarga ambas fuentes, deduplica y (opcionalmente) escribe el CSV.

    Devuelve la lista de partidos (posiblemente vacía). Nunca inventa datos.
    """
    merged: dict[tuple, dict] = {}
    for row in _load_football_data_couk() + _load_football_data_org():
        if row["date"] < MIN_DATE:
            continue
        key = (row["home_team"], row["away_team"], row["date"])
        merged.setdefault(key, row)

    rows = sorted(merged.values(), key=lambda r: r["date"])

    if write:
        _write_csv(rows)

    _print_stats(rows)
    return rows


def _write_csv(rows: list[dict]) -> None:
    try:
        with open(HISTORY_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in CSV_COLUMNS})
    except OSError as exc:
        logger.error("[natloader] no pude escribir %s: %s", HISTORY_CSV, exc)


def _print_stats(rows: list[dict]) -> None:
    if not rows:
        print("[natloader] 0 partidos cargados — sin fuente disponible (CSV vacío, fallback ELO).")
        return
    teams = {r["home_team"] for r in rows} | {r["away_team"] for r in rows}
    dates = [r["date"] for r in rows]
    print(
        f"[natloader] {len(rows)} partidos · rango {min(dates)}–{max(dates)} · {len(teams)} selecciones"
    )


def refresh_if_stale(max_age_hours: int = 24) -> list[dict]:
    """Refresca el CSV si falta o tiene más de `max_age_hours`. Devuelve los partidos."""
    if HISTORY_CSV.exists():
        age_h = (datetime.now(timezone.utc).timestamp() - HISTORY_CSV.stat().st_mtime) / 3600.0
        if age_h < max_age_hours:
            return read_history()
    return load_and_merge(write=True)


def read_history() -> list[dict]:
    """Lee el CSV persistido. Devuelve [] si no existe."""
    if not HISTORY_CSV.exists():
        return []
    out: list[dict] = []
    try:
        with open(HISTORY_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                hg, ag = _to_int(r.get("home_goals")), _to_int(r.get("away_goals"))
                if hg is None or ag is None:
                    continue
                out.append({
                    "date": r.get("date"), "home_team": r.get("home_team"),
                    "away_team": r.get("away_team"), "home_goals": hg, "away_goals": ag,
                    "competition": r.get("competition", ""), "stage": r.get("stage", ""),
                })
    except OSError as exc:
        logger.warning("[natloader] no pude leer %s: %s", HISTORY_CSV, exc)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_and_merge(write=True)
