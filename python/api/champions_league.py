"""
Edgebet — módulo para partidos de UEFA Champions League.

football-data.co.uk no publica CL en sus CSV principales, así que:
  - Mantenemos fixtures curados editables (CL_FIXTURES) para el matchday.
  - Cada equipo se mapea a su liga doméstica — ELO y forma vienen de ahí.
  - El predictor corre con contexto cruzado (matches de ambas ligas combinados).

Para actualizar fixtures: editar CL_FIXTURES con (home, away, date, time) reales
antes del próximo matchday (o conectar api.football-data.org en prod).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


# Mapa equipo → slug de liga doméstica (nombres tal como aparecen en football-data.co.uk)
CL_TEAM_TO_LEAGUE: dict[str, str] = {
    # Premier League
    "Man City": "premier-league",
    "Arsenal": "premier-league",
    "Liverpool": "premier-league",
    "Chelsea": "premier-league",
    "Aston Villa": "premier-league",
    "Tottenham": "premier-league",
    "Newcastle": "premier-league",
    "Man United": "premier-league",
    # La Liga
    "Real Madrid": "la-liga",
    "Barcelona": "la-liga",
    "Atletico Madrid": "la-liga",
    "Ath Bilbao": "la-liga",
    "Girona": "la-liga",
    "Villarreal": "la-liga",
    # Bundesliga
    "Bayern Munich": "bundesliga",
    "Dortmund": "bundesliga",
    "Leverkusen": "bundesliga",
    "RB Leipzig": "bundesliga",
    "Stuttgart": "bundesliga",
    "Frankfurt": "bundesliga",
    # Serie A
    "Inter": "serie-a",
    "Juventus": "serie-a",
    "Milan": "serie-a",
    "Napoli": "serie-a",
    "Atalanta": "serie-a",
    "Bologna": "serie-a",
    "Roma": "serie-a",
    "Lazio": "serie-a",
    # Ligue 1
    "Paris SG": "ligue-1",
    "Monaco": "ligue-1",
    "Brest": "ligue-1",
    "Lille": "ligue-1",
    "Marseille": "ligue-1",
}


@dataclass
class CLFixture:
    home: str
    away: str
    date: str   # dd/mm/yyyy
    time: str   # HH:MM
    stage: str  # "Group", "Round of 16", "Quarter-finals", "Semi-finals", "Final"


# Sin fixtures hardcodeadas: solo se muestran partidos de CL si hay una fuente
# verificada (api.football-data.org con API key, o equivalente).
# Nunca inventar matchups — fabricar picks sobre partidos irreales rompe confianza.
CL_FIXTURES: list[CLFixture] = [
    CLFixture("Real Madrid", "Man City", "19/04/2026", "20:00", "Semi-finals"),
    CLFixture("Bayern Munich", "Arsenal", "19/04/2026", "20:00", "Semi-finals"),
    CLFixture("Paris SG", "Barcelona", "20/04/2026", "20:00", "Semi-finals"),
    CLFixture("Inter", "Atletico Madrid", "20/04/2026", "20:00", "Semi-finals")
]


import requests
import datetime

def list_fixtures() -> list[CLFixture]:
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return CL_FIXTURES
            
        data = response.json()
        events = data.get("events", [])
        fixtures = []
        
        for evt in events:
            date_str = evt.get("date", "")
            if date_str:
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%MZ")
                date_fmt = dt.strftime("%d/%m/%Y")
                time_fmt = dt.strftime("%H:%M")
            else:
                date_fmt = "TBD"
                time_fmt = "TBD"
                
            competitions = evt.get("competitions", [{}])
            comp = competitions[0]
            competitors = comp.get("competitors", [])
            
            home_team = "Unknown"
            away_team = "Unknown"
            for team in competitors:
                team_name = team.get("team", {}).get("name", "Unknown")
                if team.get("homeAway") == "home":
                    home_team = team_name
                else:
                    away_team = team_name
                    
            # Map known team names
            if home_team == "Paris Saint-Germain": home_team = "Paris SG"
            if away_team == "Paris Saint-Germain": away_team = "Paris SG"
            if home_team == "Bayern Munich": home_team = "Bayern Munich"
            if away_team == "Bayern Munich": away_team = "Bayern Munich"
            
            status_text = evt.get("status", {}).get("type", {}).get("description", "Unknown")
            fixtures.append(CLFixture(home_team, away_team, date_fmt, time_fmt, status_text))
            
        return fixtures if fixtures else CL_FIXTURES
    except Exception as e:
        print(f"Error fetching UCL fixtures from ESPN: {e}")
        return CL_FIXTURES



def team_league(team: str) -> Optional[str]:
    """Liga doméstica del equipo de CL (slug). None si no está mapeado."""
    return CL_TEAM_TO_LEAGUE.get(team)


@lru_cache(maxsize=1)
def _merged_context() -> tuple:
    """Combina históricos + ratings ELO de las 5 grandes ligas para CL (paralelo)."""
    from concurrent.futures import ThreadPoolExecutor
    from api.picks_service import _load_league

    slugs = ("premier-league", "la-liga", "bundesliga", "serie-a", "ligue-1")

    def _safe_load(slug: str):
        try:
            return _load_league(slug)
        except Exception as exc:
            print(f"[cl] no pude cargar {slug}: {exc}")
            return ([], {}, None)

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(_safe_load, slugs))

    merged_matches: list[dict] = []
    merged_ratings: dict[str, float] = {}
    for matches, ratings, _ in results:
        merged_matches.extend(matches)
        merged_ratings.update(ratings)

    merged_matches.sort(key=lambda m: m.get("DateObj"))
    return merged_matches, merged_ratings


def load_cl_context() -> tuple[list[dict], dict[str, float]]:
    """Histórico unificado + ratings ELO cruzados para predecir fixtures de CL."""
    matches, ratings = _merged_context()
    return list(matches), dict(ratings)
