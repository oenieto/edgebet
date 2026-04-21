import csv
import hashlib
import io
import time
import urllib.request
import math
from datetime import datetime
from pathlib import Path

LEAGUES_MAP = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "D1": "Bundesliga",
    "I1": "Serie A",
    "F1": "Ligue 1",
}

# Cache directory — persiste entre reinicios
_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# TTL por URL. Históricos de temporadas cerradas son inmutables (TTL gigante).
# fixtures.csv cambia durante la semana → 15 min.
_HISTORY_TTL = 7 * 24 * 3600      # 7 días para CSV de seasons (son inmutables pero permitimos refresco)
_FIXTURES_TTL = 15 * 60           # 15 min para fixtures.csv
_NETWORK_TIMEOUT = 6              # 6s en vez de 10s: falla rápido y usa cache

# Memoria: evita siquiera tocar disco dentro del mismo proceso
_mem_cache: dict[str, tuple[float, list[dict]]] = {}


def _cache_path_for(url: str) -> Path:
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    return _CACHE_DIR / f"{h}.csv"


def _ttl_for(url: str) -> int:
    return _FIXTURES_TTL if url.endswith("/fixtures.csv") else _HISTORY_TTL


def _parse_rows(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _read_disk_cache(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    try:
        return _parse_rows(path.read_bytes())
    except Exception:
        return None


def fetch_csv(url: str) -> list[dict]:
    """
    Fetch con 3 niveles de cache: memoria → disco (dentro de TTL) → red.
    Si la red falla, cae al disco stale (mejor servir datos viejos que nada).
    """
    now = time.time()

    mem = _mem_cache.get(url)
    if mem and (now - mem[0]) < _ttl_for(url):
        return mem[1]

    cache_path = _cache_path_for(url)
    if cache_path.exists():
        age = now - cache_path.stat().st_mtime
        if age < _ttl_for(url):
            rows = _read_disk_cache(cache_path)
            if rows:
                _mem_cache[url] = (now, rows)
                return rows

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=_NETWORK_TIMEOUT) as response:
            raw = response.read()
        rows = _parse_rows(raw)
        try:
            cache_path.write_bytes(raw)
        except Exception:
            pass
        _mem_cache[url] = (now, rows)
        return rows
    except Exception as exc:
        # Red falló → último recurso: cache stale en disco
        stale = _read_disk_cache(cache_path)
        if stale:
            print(f"[cache] red falló para {url.split('/')[-1]}, uso stale ({len(stale)} rows)")
            _mem_cache[url] = (now, stale)  # refresca TTL de memoria
            return stale
        print(f"Error fetching {url}: {exc}")
        return []

def load_history(league_code: str, seasons: list[str]) -> list[dict]:
    """Descarga todas las temporadas en paralelo (hasta ~4x más rápido que serie)."""
    from concurrent.futures import ThreadPoolExecutor

    urls = [
        f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv"
        for season in seasons
    ]
    with ThreadPoolExecutor(max_workers=min(8, len(urls) or 1)) as ex:
        season_batches = list(ex.map(fetch_csv, urls))

    matches: list[dict] = []
    for season_matches in season_batches:
        for m in season_matches:
            if m and m.get("HomeTeam") and m.get("AwayTeam") and m.get("FTR") and m.get("Date"):
                try:
                    m["DateObj"] = datetime.strptime(m["Date"], "%d/%m/%Y")
                except ValueError:
                    try:
                        m["DateObj"] = datetime.strptime(m["Date"], "%d/%m/%y")
                    except ValueError:
                        m["DateObj"] = datetime.min
                matches.append(m)
    matches.sort(key=lambda x: x["DateObj"])
    return matches

def compute_elo(matches: list[dict], k: int = 32, home_advantage: int = 65) -> dict:
    ratings = {}
    
    def get_rating(team: str) -> float:
        return ratings.setdefault(team, 1500.0)
        
    for m in matches:
        home = m["HomeTeam"]
        away = m["AwayTeam"]
        try:
            fthg = int(m["FTHG"])
            ftag = int(m["FTAG"])
        except (ValueError, KeyError, TypeError):
            continue
            
        r_home = get_rating(home) + home_advantage
        r_away = get_rating(away)
        e_home = 1.0 / (1.0 + 10 ** ((r_away - r_home) / 400.0))
        e_away = 1.0 - e_home
        
        if fthg > ftag:
            s_home, s_away = 1.0, 0.0
        elif fthg < ftag:
            s_home, s_away = 0.0, 1.0
        else:
            s_home, s_away = 0.5, 0.5
            
        margin = math.log(abs(fthg - ftag) + 1)
        ratings[home] += k * margin * (s_home - e_home)
        ratings[away] += k * margin * (s_away - e_away)
        
    return ratings

def load_fixtures(leagues: list[str]) -> list[dict]:
    url = "https://www.football-data.co.uk/fixtures.csv"
    matches = fetch_csv(url)
    fixtures = []
    for m in matches:
        if m and m.get("Div") in leagues:
            m["League"] = LEAGUES_MAP.get(m["Div"], m["Div"])
            fixtures.append(m)
    return fixtures

def compute_team_form(matches: list[dict], team: str, n: int = 5) -> dict:
    recent = [m for m in matches if m["HomeTeam"] == team or m["AwayTeam"] == team][-n:]
    gf, ga, shots, sot, corners, pts = [], [], [], [], [], []
    for row in recent:
        is_home = row["HomeTeam"] == team

        def safe_int(val, default=0):
            try:
                return int(val)
            except (TypeError, ValueError):
                return default

        gf.append(safe_int(row.get("FTHG") if is_home else row.get("FTAG")))
        ga.append(safe_int(row.get("FTAG") if is_home else row.get("FTHG")))
        shots.append(safe_int(row.get("HS") if is_home else row.get("AS")))
        sot.append(safe_int(row.get("HST") if is_home else row.get("AST")))
        corners.append(safe_int(row.get("HC") if is_home else row.get("AC")))

        ftr = row.get("FTR")
        if is_home:
            pts.append(3 if ftr == "H" else (1 if ftr == "D" else 0))
        else:
            pts.append(3 if ftr == "A" else (1 if ftr == "D" else 0))

    n_played = len(gf) or 1
    return {
        "avg_GF": sum(gf) / n_played,
        "avg_GA": sum(ga) / n_played,
        "avg_Shots": sum(shots) / n_played,
        "avg_SoT": sum(sot) / n_played,
        "avg_Corners": sum(corners) / n_played,
        "Form": sum(pts) / n_played,
        "matches_counted": n_played,
    }
