"""
Edgebet — mapeo canónico de nombres de selecciones.

Une las variantes de nombres de TODAS las fuentes (martj42/international_results,
football-data.org, etc.) a una forma canónica. Para las 48 selecciones del
Mundial 2026, la forma canónica DEBE coincidir con las claves de
`api.world_cup.WORLD_CUP_TEAM_ELOS` para que el predictor las encuentre.

Nota: las claves de world_cup.py usan ASCII — p.ej. "USA" y "Curacao" (sin
cedilla). Por eso aquí "United States"→"USA" y "Curaçao"→"Curacao" (al revés del
ejemplo del brief, que apuntaba a "Curaçao"); si no, predict() no haría match.
"""
from __future__ import annotations

TEAM_NAME_MAP: dict[str, str] = {
    # --- USA (clave world_cup: "USA") ---
    "United States": "USA",
    "United States of America": "USA",
    "US": "USA",
    "USMNT": "USA",
    "USA": "USA",

    # --- Curaçao (clave world_cup: "Curacao") ---
    "Curaçao": "Curacao",
    "Curacao": "Curacao",

    # --- Inglaterra ---
    "England": "England",
    "Three Lions": "England",

    # --- Irán ---
    "IR Iran": "Iran",
    "Iran (Islamic Republic of)": "Iran",
    "Islamic Republic of Iran": "Iran",
    "Iran": "Iran",

    # --- Coreas ---
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "South Korea": "South Korea",
    "Korea DPR": "North Korea",
    "DPR Korea": "North Korea",
    "North Korea": "North Korea",

    # --- Costa de Marfil ---
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",

    # --- Cabo Verde ---
    "Cape Verde Islands": "Cape Verde",
    "Cabo Verde": "Cape Verde",
    "Cape Verde": "Cape Verde",

    # --- Congo RD ---
    "DR Congo": "Congo DR",
    "Congo DR": "Congo DR",
    "Democratic Republic of the Congo": "Congo DR",
    "Congo (DR)": "Congo DR",

    # --- Trinidad y Tobago ---
    "Trinidad & Tobago": "Trinidad and Tobago",
    "Trinidad and Tobago": "Trinidad and Tobago",

    # --- Bosnia ---
    "Bosnia & Herzegovina": "Bosnia",
    "Bosnia and Herzegovina": "Bosnia",
    "Bosnia-Herzegovina": "Bosnia",
    "Bosnia": "Bosnia",

    # --- Macedonia del Norte ---
    "North Macedonia": "North Macedonia",
    "Republic of North Macedonia": "North Macedonia",
    "Macedonia": "North Macedonia",

    # --- Chequia ---
    "Czech Republic": "Czechia",
    "Czechia": "Czechia",

    # --- Otras variantes comunes ---
    "Kyrgyz Republic": "Kyrgyzstan",
    "Kyrgyzstan": "Kyrgyzstan",
    "Chinese Taipei": "Taiwan",
    "Taiwan": "Taiwan",
    "China PR": "China",
    "China": "China",
    "Cape Verde": "Cape Verde",
    "Saudi Arabia": "Saudi Arabia",
    "Republic of Ireland": "Ireland",
    "Ireland": "Ireland",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Turkey": "Turkey",
    "UAE": "United Arab Emirates",
    "Brunei Darussalam": "Brunei",
    "St Kitts and Nevis": "Saint Kitts and Nevis",
    "St Vincent and the Grenadines": "Saint Vincent and the Grenadines",
    "St Lucia": "Saint Lucia",
    "Cabo Verde Islands": "Cape Verde",
}


def canonicalize(name: str | None) -> str:
    """Devuelve la forma canónica de un nombre de selección.

    Match exacto sobre el nombre recortado; si no hay alias, devuelve el nombre
    tal cual (recortado). Las 48 del Mundial caen en claves de world_cup.py.
    """
    if not name:
        return ""
    key = name.strip()
    return TEAM_NAME_MAP.get(key, key)
