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


# Fixtures curados del próximo matchday CL (actualizar antes de cada jornada).
# Idealmente conectar api.football-data.org en prod para auto-feed; mientras,
# los nombres deben coincidir EXACTO con los keys de CL_TEAM_TO_LEAGUE para
# que la búsqueda de histórico/forma funcione.
CL_FIXTURES: list[CLFixture] = [
    # Cuartos — vuelta (calendario UEFA 2025/26)
    CLFixture(home="Man City", away="Real Madrid", date="07/05/2026", time="20:00", stage="Quarter-finals"),
    CLFixture(home="Arsenal", away="Bayern Munich", date="07/05/2026", time="20:00", stage="Quarter-finals"),
    CLFixture(home="Paris SG", away="Barcelona", date="08/05/2026", time="20:00", stage="Quarter-finals"),
    CLFixture(home="Atletico Madrid", away="Dortmund", date="08/05/2026", time="20:00", stage="Quarter-finals"),
    # Semis (placeholder — se ajustan tras los cuartos)
    CLFixture(home="Real Madrid", away="Bayern Munich", date="14/05/2026", time="20:00", stage="Semi-finals"),
    CLFixture(home="Barcelona", away="Dortmund", date="15/05/2026", time="20:00", stage="Semi-finals"),
]


def list_fixtures() -> list[CLFixture]:
    """Devuelve los fixtures curados. Extensible a API remota en el futuro."""
    return list(CL_FIXTURES)


def team_league(team: str) -> Optional[str]:
    """Liga doméstica del equipo de CL (slug). None si no está mapeado."""
    return CL_TEAM_TO_LEAGUE.get(team)


@lru_cache(maxsize=1)
def _merged_context() -> tuple:
    """Combina históricos + ratings ELO de las 5 grandes ligas para CL (paralelo).

    Antes importaba `picks_service._load_league` y creaba un ciclo de imports.
    Ahora llama directamente a los loaders/elo, manteniendo `picks_service`
    libre de dependencia hacia este módulo a nivel de carga.
    """
    from concurrent.futures import ThreadPoolExecutor
    from api.openfootball_loader import load_history_of
    from api.fast_loader import compute_elo

    slugs = ("premier-league", "la-liga", "bundesliga", "serie-a", "ligue-1")

    def _safe_load(slug: str):
        try:
            matches = load_history_of(slug)
            ratings = compute_elo(matches, k=32, home_advantage=65)
            return matches, ratings
        except Exception as exc:
            print(f"[cl] no pude cargar {slug}: {exc}")
            return ([], {})

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(_safe_load, slugs))

    merged_matches: list[dict] = []
    merged_ratings: dict[str, float] = {}
    for matches, ratings in results:
        merged_matches.extend(matches)
        merged_ratings.update(ratings)

    merged_matches.sort(key=lambda m: m.get("DateObj") or "")
    return merged_matches, merged_ratings


def load_cl_context() -> tuple[list[dict], dict[str, float]]:
    """Histórico unificado + ratings ELO cruzados para predecir fixtures de CL."""
    matches, ratings = _merged_context()
    return list(matches), dict(ratings)
