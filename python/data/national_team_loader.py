"""
Edgebet — loader de histórico de selecciones nacionales (desde 2019).

Alimenta al PoissonPredictor con partidos reales para que las probabilidades
del Mundial pasen de ELO puro a Poisson basado en goles reales.

Fuentes libres (verificadas 2026-06-17):
  A) football-data.co.uk — sin CSV de selecciones en ruta estable (404). Stub.
  B) football-data.org REST — requiere FOOTBALL_DATA_API_KEY. Free tier: solo
     temporada actual de WC + EC (WCQ/CONC/CAN/CA → 404). Aporta WC 2026 en vivo.
  C) openfootball GitHub JSON — TODAS las URLs del plan original responden 404
     (los repos/paths no existen). Deshabilitado; se reactiva si openfootball
     vuelve a publicarlas.
  D) martj42/international_results (GitHub) — CSV exhaustivo 1872–presente, TODAS
     las confederaciones. Filtrado a >=2019 da ~7k partidos de selecciones. Es la
     fuente principal de cobertura.
  E) FIFA ranking — fuente 404; corrección de seed ELO omitida (el histórico ya
     recalibra el ELO desde resultados reales).

Regla dura del proyecto: si una URL falla, se omite — NUNCA se inventan datos.
"""
from __future__ import annotations

import csv
import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from data.team_name_map import canonicalize

logger = logging.getLogger("edgebet.natloader")

DATA_DIR = Path(__file__).resolve().parent
HISTORY_CSV = DATA_DIR / "national_teams_history.csv"

CSV_COLUMNS = ["date", "home_team", "away_team", "home_goals", "away_goals", "competition", "source"]

MIN_DATE = "2019-01-01"
_REQUEST_TIMEOUT = 25


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
        if v is None or v == "" or v == "NA":
            return None
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _get(url: str, *, headers: dict | None = None, retries: int = 1) -> requests.Response | None:
    """GET con reintento simple en errores de conexión. None si falla."""
    for attempt in range(retries + 1):
        try:
            return requests.get(url, headers=headers, timeout=_REQUEST_TIMEOUT)
        except requests.exceptions.ConnectionError as exc:
            if attempt >= retries:
                logger.warning("[natloader] conexión falló %s: %s", url, exc)
                return None
        except requests.RequestException as exc:
            logger.warning("[natloader] red falló %s: %s", url, exc)
            return None
    return None


# ---------------------------------------------------------------------------
# SOURCE A — football-data.co.uk (sin CSV de selecciones → stub)
# ---------------------------------------------------------------------------
def _load_football_data_couk() -> list[dict]:
    logger.info("[natloader] A: football-data.co.uk sin CSV de selecciones (404) — omitido.")
    return []


# ---------------------------------------------------------------------------
# SOURCE B — football-data.org REST API (WC + EC; el resto 403/404)
# ---------------------------------------------------------------------------
_FDORG_COMPETITIONS = ["WC", "EC"]
_FDORG_BASE = "https://api.football-data.org/v4/competitions"


def _load_football_data_org() -> list[dict]:
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        logger.warning("[natloader] B: FOOTBALL_DATA_API_KEY ausente — omitido.")
        return []

    headers = {"X-Auth-Token": api_key}
    rows: list[dict] = []
    skipped: list[str] = []
    for comp in _FDORG_COMPETITIONS:
        resp = _get(f"{_FDORG_BASE}/{comp}/matches?status=FINISHED", headers=headers)
        if resp is None:
            skipped.append(f"{comp}(red)")
            continue
        if resp.status_code != 200:
            skipped.append(f"{comp}({resp.status_code})")
            continue
        try:
            data = resp.json()
        except ValueError:
            skipped.append(f"{comp}(json)")
            continue
        comp_name = (data.get("competition") or {}).get("name") or comp
        for m in data.get("matches", []):
            if m.get("status") != "FINISHED":
                continue
            ft = (m.get("score") or {}).get("fullTime") or {}
            hg, ag = _to_int(ft.get("home")), _to_int(ft.get("away"))
            date = _parse_date(m.get("utcDate"))
            home = (m.get("homeTeam") or {}).get("name", "")
            away = (m.get("awayTeam") or {}).get("name", "")
            if hg is None or ag is None or not (date and home and away):
                continue
            rows.append({
                "date": date, "home_team": home, "away_team": away,
                "home_goals": hg, "away_goals": ag,
                "competition": comp_name, "source": "football_data_org",
            })
    if skipped:
        logger.warning("[natloader] B: omitidas %s", ", ".join(skipped))
    logger.info("[natloader] B: %d partidos (football-data.org)", len(rows))
    return rows


# ---------------------------------------------------------------------------
# SOURCE C — openfootball (todas las URLs del plan original = 404 → deshabilitado)
# ---------------------------------------------------------------------------
def _load_openfootball() -> list[dict]:
    logger.info("[natloader] C: openfootball deshabilitado (URLs 404 verificadas) — omitido.")
    return []


# ---------------------------------------------------------------------------
# SOURCE D — martj42/international_results (CSV exhaustivo, todas las confeds)
# ---------------------------------------------------------------------------
_MARTJ42_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"


def _load_martj42() -> list[dict]:
    resp = _get(_MARTJ42_URL)
    if resp is None or resp.status_code != 200:
        code = resp.status_code if resp is not None else "red"
        logger.warning("[natloader] D: martj42 no disponible (%s) — omitido.", code)
        return []
    rows: list[dict] = []
    try:
        reader = csv.DictReader(io.StringIO(resp.text))
        for r in reader:
            date = _parse_date(r.get("date"))
            if not date or date < MIN_DATE:
                continue
            hg, ag = _to_int(r.get("home_score")), _to_int(r.get("away_score"))
            home, away = r.get("home_team", ""), r.get("away_team", "")
            if hg is None or ag is None or not (home and away):
                continue
            rows.append({
                "date": date, "home_team": home, "away_team": away,
                "home_goals": hg, "away_goals": ag,
                "competition": r.get("tournament") or "International",
                "source": "martj42",
            })
    except Exception as exc:
        logger.warning("[natloader] D: parse martj42 falló: %s", exc)
        return []
    logger.info("[natloader] D: %d partidos >=%s (martj42)", len(rows), MIN_DATE)
    return rows


# ---------------------------------------------------------------------------
# Orquestación: cargar todo, normalizar, deduplicar, validar, guardar
# ---------------------------------------------------------------------------
def load_all_sources(write: bool = True) -> list[dict]:
    """Llama a todas las fuentes, mapea nombres, deduplica y (opcional) guarda CSV."""
    raw: list[dict] = []
    raw += _load_football_data_couk()
    raw += _load_football_data_org()
    raw += _load_openfootball()
    raw += _load_martj42()

    merged: dict[tuple, dict] = {}
    for row in raw:
        date = row.get("date")
        if not date or date < MIN_DATE:
            continue
        if row.get("home_goals") is None or row.get("away_goals") is None:
            continue
        home = canonicalize(row.get("home_team"))
        away = canonicalize(row.get("away_team"))
        if not home or not away:
            continue
        key = (home, away, date)
        if key in merged:
            continue  # dedup: keep first
        merged[key] = {
            "date": date, "home_team": home, "away_team": away,
            "home_goals": int(row["home_goals"]), "away_goals": int(row["away_goals"]),
            "competition": row.get("competition", ""), "source": row.get("source", ""),
        }

    rows = sorted(merged.values(), key=lambda r: r["date"])
    if write:
        _write_csv(rows)
    _print_report(rows)
    return rows


# Alias retro-compatible (scheduler / refresh_if_stale lo usan).
def load_and_merge(write: bool = True) -> list[dict]:
    return load_all_sources(write=write)


def _write_csv(rows: list[dict]) -> None:
    try:
        with open(HISTORY_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in CSV_COLUMNS})
    except OSError as exc:
        logger.error("[natloader] no pude escribir %s: %s", HISTORY_CSV, exc)


def _print_report(rows: list[dict]) -> None:
    line = "═══════════════════════════════════════════"
    print(line)
    print("NATIONAL TEAM DATA PIPELINE — FINAL REPORT")
    print(line)
    if not rows:
        print("Total matches loaded:  0 — sin fuente disponible (CSV vacío, fallback ELO).")
        print(line)
        return

    dates = [r["date"] for r in rows]
    teams = {r["home_team"] for r in rows} | {r["away_team"] for r in rows}
    by_source: dict[str, int] = {}
    for r in rows:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1

    print(f"Total matches loaded:  {len(rows)}")
    print(f"Date range:            {min(dates)} → {max(dates)}")
    print(f"Unique teams:          {len(teams)}")
    print("")
    print("By source:")
    for s in ("football_data_org", "football_data_co_uk", "openfootball", "martj42"):
        if by_source.get(s):
            print(f"  {s:20s} {by_source[s]} matches")
    print("")

    # Cobertura por selección del Mundial 2026 + por confederación.
    try:
        from api.world_cup import all_teams
        wc = all_teams()
    except Exception:
        wc = []

    if wc:
        per_team: dict[str, int] = {}
        for r in rows:
            for t in (r["home_team"], r["away_team"]):
                per_team[t] = per_team.get(t, 0) + 1

        conf: dict[str, list[int]] = {}
        for t in wc:
            n = per_team.get(t.key, 0)
            conf.setdefault(t.confederation, []).append(n)
        print("By confederation (WC 2026 teams):")
        for cf in ("UEFA", "CONMEBOL", "CAF", "AFC", "CONCACAF", "OFC"):
            if cf in conf:
                vals = conf[cf]
                print(f"  {cf:9s} ({len(vals)} teams): avg {sum(vals)/len(vals):.1f} matches/team")
        print("")
        print("Coverage per WC 2026 team (desc):")
        ranked = sorted(wc, key=lambda t: per_team.get(t.key, 0), reverse=True)
        for t in ranked:
            n = per_team.get(t.key, 0)
            icon = "✅" if n >= 8 else "⚡"
            print(f"  {icon} {t.name:18s} — {n} matches" + ("" if n >= 8 else " (ELO fallback)"))
    print(line)


def refresh_if_stale(max_age_hours: int = 24) -> list[dict]:
    """Refresca el CSV si falta o supera `max_age_hours`. Devuelve los partidos."""
    if HISTORY_CSV.exists():
        age_h = (datetime.now(timezone.utc).timestamp() - HISTORY_CSV.stat().st_mtime) / 3600.0
        if age_h < max_age_hours:
            return read_history()
    return load_all_sources(write=True)


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
                    "competition": r.get("competition", ""), "source": r.get("source", ""),
                })
    except OSError as exc:
        logger.warning("[natloader] no pude leer %s: %s", HISTORY_CSV, exc)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_all_sources(write=True)
