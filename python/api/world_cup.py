"""
Edgebet — módulo para partidos de la Copa del Mundo FIFA 2026.

Mantiene:
  - ELO de selecciones nacionales inicial calibrado.
  - Fixtures curados de la Copa del Mundo FIFA 2026.
  - Método de carga de contexto cruzado (histórico + ELO).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ELO inicial calibrado de selecciones (Ranking FIFA / Elo ratings 2026)
WORLD_CUP_TEAM_ELOS: dict[str, float] = {
    "Argentina": 1860.0,
    "France": 1845.0,
    "Spain": 1830.0,
    "England": 1815.0,
    "Brazil": 1810.0,
    "Portugal": 1790.0,
    "Netherlands": 1785.0,
    "Italy": 1770.0,
    "Germany": 1765.0,
    "Belgium": 1750.0,
    "Croatia": 1740.0,
    "Uruguay": 1735.0,
    "Morocco": 1720.0,
    "Colombia": 1715.0,
    "USA": 1690.0,
    "Mexico": 1680.0,
    "Japan": 1675.0,
    "Senegal": 1660.0,
    "Switzerland": 1655.0,
    "Denmark": 1650.0,
    "Ecuador": 1640.0,
    "Iran": 1620.0,
    "South Korea": 1615.0,
    "Ukraine": 1610.0,
    "Australia": 1600.0,
    "Canada": 1590.0,
    "Saudi Arabia": 1580.0,
    "Cameroon": 1570.0,
    "Costa Rica": 1560.0,
    # Resto de selecciones del bracket curado 2026 (estimaciones por tier FIFA).
    "Norway": 1665.0,
    "Serbia": 1640.0,
    "Poland": 1630.0,
    "Nigeria": 1625.0,
    "Egypt": 1605.0,
    "Algeria": 1600.0,
    "Ivory Coast": 1595.0,
    "Ghana": 1580.0,
    "Tunisia": 1565.0,
    "Qatar": 1560.0,
    "Paraguay": 1560.0,
    "Venezuela": 1545.0,
    "South Africa": 1545.0,
    "Panama": 1535.0,
    "Uzbekistan": 1535.0,
    "Jordan": 1520.0,
    "Iraq": 1500.0,
    "New Zealand": 1485.0,
    "Curacao": 1455.0,
}


@dataclass
class WCFixture:
    home: str
    away: str
    date: str   # dd/mm/yyyy
    time: str   # HH:MM
    stage: str  # "Group", "Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final"
    group: Optional[str] = None


# Fixtures de la Copa del Mundo 2026 (fase de grupos inicial curada para tests / demo)
WC_FIXTURES: list[WCFixture] = [
    WCFixture(home="Mexico", away="USA", date="11/06/2026", time="18:00", stage="Group", group="A"),
    WCFixture(home="Canada", away="Ecuador", date="12/06/2026", time="16:00", stage="Group", group="B"),
    WCFixture(home="Argentina", away="Saudi Arabia", date="13/06/2026", time="15:00", stage="Group", group="C"),
    WCFixture(home="France", away="Australia", date="14/06/2026", time="20:00", stage="Group", group="D"),
    WCFixture(home="Spain", away="Costa Rica", date="15/06/2026", time="17:00", stage="Group", group="E"),
    WCFixture(home="England", away="Iran", date="16/06/2026", time="14:00", stage="Group", group="F"),
    WCFixture(home="Argentina", away="France", date="18/06/2026", time="20:00", stage="Group", group="G"),
    WCFixture(home="Brazil", away="Germany", date="19/06/2026", time="18:00", stage="Group", group="H"),
]


def list_fixtures() -> list[WCFixture]:
    """Devuelve los fixtures de la Copa del Mundo 2026."""
    return list(WC_FIXTURES)


def load_wc_context() -> tuple[list[dict], dict[str, float]]:
    """Devuelve histórico simulado (vacío por ahora) y el ranking ELO inicial de selecciones."""
    # Como es un torneo corto y no hay liga doméstica persistente, empezamos
    # con los ratings ELO base de selecciones. A medida que avancen los partidos,
    # el motor ELO del pipeline los actualizará si hay histórico.
    return [], dict(WORLD_CUP_TEAM_ELOS)


# ============================================================================
# BRACKET CURADO — Copa del Mundo FIFA 2026 (48 selecciones, grupos A–L)
# ============================================================================
# ⚠️  DATOS CURADOS / BORRADOR — VERIFICAR contra el sorteo oficial de la FIFA.
#
# Las asignaciones de grupo son un borrador editable: cada selección y su
# confederación son correctas, pero la distribución exacta por grupo DEBE
# confirmarse contra el sorteo oficial (5 dic 2025). La `key` enlaza con
# WORLD_CUP_TEAM_ELOS (canónico en inglés); `name` es el display en español.
# Para corregir el bracket, edita solo esta estructura — el endpoint la lee tal
# cual y nunca inventa datos.

@dataclass
class WCTeam:
    name: str           # display en español ("México")
    key: str            # clave canónica (enlaza con WORLD_CUP_TEAM_ELOS)
    flag: str           # emoji de bandera
    confederation: str  # UEFA | CONMEBOL | CONCACAF | CAF | AFC | OFC
    group: str          # 'A'..'L'


def _t(name: str, key: str, flag: str, conf: str, group: str) -> WCTeam:
    return WCTeam(name=name, key=key, flag=flag, confederation=conf, group=group)


WORLD_CUP_2026_GROUPS: dict[str, list[WCTeam]] = {
    "A": [
        _t("México", "Mexico", "🇲🇽", "CONCACAF", "A"),
        _t("Croacia", "Croatia", "🇭🇷", "UEFA", "A"),
        _t("Ecuador", "Ecuador", "🇪🇨", "CONMEBOL", "A"),
        _t("Arabia Saudita", "Saudi Arabia", "🇸🇦", "AFC", "A"),
    ],
    "B": [
        _t("Canadá", "Canada", "🇨🇦", "CONCACAF", "B"),
        _t("Bélgica", "Belgium", "🇧🇪", "UEFA", "B"),
        _t("Marruecos", "Morocco", "🇲🇦", "CAF", "B"),
        _t("Catar", "Qatar", "🇶🇦", "AFC", "B"),
    ],
    "C": [
        _t("Estados Unidos", "USA", "🇺🇸", "CONCACAF", "C"),
        _t("Suiza", "Switzerland", "🇨🇭", "UEFA", "C"),
        _t("Uruguay", "Uruguay", "🇺🇾", "CONMEBOL", "C"),
        _t("Corea del Sur", "South Korea", "🇰🇷", "AFC", "C"),
    ],
    "D": [
        _t("Argentina", "Argentina", "🇦🇷", "CONMEBOL", "D"),
        _t("Noruega", "Norway", "🇳🇴", "UEFA", "D"),
        _t("Túnez", "Tunisia", "🇹🇳", "CAF", "D"),
        _t("Australia", "Australia", "🇦🇺", "AFC", "D"),
    ],
    "E": [
        _t("Francia", "France", "🇫🇷", "UEFA", "E"),
        _t("Senegal", "Senegal", "🇸🇳", "CAF", "E"),
        _t("Japón", "Japan", "🇯🇵", "AFC", "E"),
        _t("Paraguay", "Paraguay", "🇵🇾", "CONMEBOL", "E"),
    ],
    "F": [
        _t("España", "Spain", "🇪🇸", "UEFA", "F"),
        _t("Egipto", "Egypt", "🇪🇬", "CAF", "F"),
        _t("Irán", "Iran", "🇮🇷", "AFC", "F"),
        _t("Costa Rica", "Costa Rica", "🇨🇷", "CONCACAF", "F"),
    ],
    "G": [
        _t("Inglaterra", "England", "🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f", "UEFA", "G"),
        _t("Colombia", "Colombia", "🇨🇴", "CONMEBOL", "G"),
        _t("Costa de Marfil", "Ivory Coast", "🇨🇮", "CAF", "G"),
        _t("Nueva Zelanda", "New Zealand", "🇳🇿", "OFC", "G"),
    ],
    "H": [
        _t("Brasil", "Brazil", "🇧🇷", "CONMEBOL", "H"),
        _t("Países Bajos", "Netherlands", "🇳🇱", "UEFA", "H"),
        _t("Argelia", "Algeria", "🇩🇿", "CAF", "H"),
        _t("Jordania", "Jordan", "🇯🇴", "AFC", "H"),
    ],
    "I": [
        _t("Portugal", "Portugal", "🇵🇹", "UEFA", "I"),
        _t("Nigeria", "Nigeria", "🇳🇬", "CAF", "I"),
        _t("Panamá", "Panama", "🇵🇦", "CONCACAF", "I"),
        _t("Uzbekistán", "Uzbekistan", "🇺🇿", "AFC", "I"),
    ],
    "J": [
        _t("Alemania", "Germany", "🇩🇪", "UEFA", "J"),
        _t("Polonia", "Poland", "🇵🇱", "UEFA", "J"),
        _t("Ghana", "Ghana", "🇬🇭", "CAF", "J"),
        _t("Venezuela", "Venezuela", "🇻🇪", "CONMEBOL", "J"),
    ],
    "K": [
        _t("Italia", "Italy", "🇮🇹", "UEFA", "K"),
        _t("Serbia", "Serbia", "🇷🇸", "UEFA", "K"),
        _t("Camerún", "Cameroon", "🇨🇲", "CAF", "K"),
        _t("Irak", "Iraq", "🇮🇶", "AFC", "K"),
    ],
    "L": [
        _t("Dinamarca", "Denmark", "🇩🇰", "UEFA", "L"),
        _t("Ucrania", "Ukraine", "🇺🇦", "UEFA", "L"),
        _t("Sudáfrica", "South Africa", "🇿🇦", "CAF", "L"),
        _t("Curazao", "Curacao", "🇨🇼", "CONCACAF", "L"),
    ],
}


def list_groups() -> dict[str, list[WCTeam]]:
    """Bracket curado por grupo (A–L). Ver advertencia de verificación arriba."""
    return WORLD_CUP_2026_GROUPS


def all_teams() -> list[WCTeam]:
    """Las 48 selecciones en orden de grupo."""
    return [t for g in WORLD_CUP_2026_GROUPS.values() for t in g]


def team_elo(key: str) -> float:
    """ELO curado de una selección; 1500 si no está calibrada."""
    return float(WORLD_CUP_TEAM_ELOS.get(key, 1500.0))
