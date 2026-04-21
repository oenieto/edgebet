"""
Features contextuales generadas por Claude.

Función `claude_analyze_matchup`: pide a Claude que estime en escala 0-1
factores que NO están en los datos numéricos (momentum, upset risk,
intensidad esperada). Se usan como features adicionales del ensemble
o como columnas extra del reporte.

Llama a Claude UNA VEZ por partido. El costo se acota al subset de
partidos "top" (mejores EV) — no se usa en el entrenamiento masivo.
"""
from __future__ import annotations

import json
import os
from typing import Optional

CONTEXT_SCHEMA = {
    "home_attack_strength": "float 0-1",
    "home_defense_strength": "float 0-1",
    "away_attack_strength": "float 0-1",
    "away_defense_strength": "float 0-1",
    "home_momentum": "float 0-1",
    "away_momentum": "float 0-1",
    "match_intensity_prediction": "float 0-1",
    "upset_probability": "float 0-1",
    "home_win_confidence": "float 0-1",
    "draw_likelihood": "float 0-1",
    "reasoning": "string breve (1-2 frases)",
}


def _safe_fmt(value, fmt: str = ".2f", default: str = "N/A") -> str:
    try:
        return format(float(value), fmt)
    except (TypeError, ValueError):
        return default


def claude_analyze_matchup(
    home_team: str,
    away_team: str,
    league: str,
    home_form: dict,
    away_form: dict,
) -> Optional[dict]:
    """
    Devuelve un dict con los scores 0-1 listos para usar como features.
    None si no hay API key o Claude falla.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None

    try:
        import anthropic
    except ImportError:
        return None

    prompt = f"""Eres un analista experto de fútbol. Analiza este partido y devuelve SOLO JSON
válido (sin markdown, sin comentarios) con scores en escala 0.0 a 1.0.

Partido: {home_team} (local) vs {away_team} (visitante)
Liga: {league}

Stats {home_team} (últimos 5 partidos):
- Goles marcados avg: {_safe_fmt(home_form.get('avg_GF'))}
- Goles recibidos avg: {_safe_fmt(home_form.get('avg_GA'))}
- Tiros avg: {_safe_fmt(home_form.get('avg_Shots'))}
- Tiros al arco avg: {_safe_fmt(home_form.get('avg_SoT'))}
- Forma (pts avg): {_safe_fmt(home_form.get('Form'))}

Stats {away_team} (últimos 5 partidos):
- Goles marcados avg: {_safe_fmt(away_form.get('avg_GF'))}
- Goles recibidos avg: {_safe_fmt(away_form.get('avg_GA'))}
- Tiros avg: {_safe_fmt(away_form.get('avg_Shots'))}
- Tiros al arco avg: {_safe_fmt(away_form.get('avg_SoT'))}
- Forma (pts avg): {_safe_fmt(away_form.get('Form'))}

Devuelve JSON estricto con este shape:
{{
    "home_attack_strength": <float>,
    "home_defense_strength": <float>,
    "away_attack_strength": <float>,
    "away_defense_strength": <float>,
    "home_momentum": <float>,
    "away_momentum": <float>,
    "match_intensity_prediction": <float>,
    "upset_probability": <float>,
    "home_win_confidence": <float>,
    "draw_likelihood": <float>,
    "reasoning": "<1-2 frases>"
}}"""

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
    except Exception as exc:
        print(f"[contextual] Claude falló: {type(exc).__name__}: {exc}")
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return None


def contextual_features_to_row(contextual: Optional[dict]) -> dict:
    """
    Convierte el dict de Claude a columnas prefijadas `ctx_*` listas para
    concatenar a la fila de features del modelo. Si es None, devuelve dict vacío.
    """
    if not contextual:
        return {}
    keys = [
        "home_attack_strength", "home_defense_strength",
        "away_attack_strength", "away_defense_strength",
        "home_momentum", "away_momentum",
        "match_intensity_prediction", "upset_probability",
        "home_win_confidence", "draw_likelihood",
    ]
    out = {}
    for k in keys:
        try:
            out[f"ctx_{k}"] = float(contextual.get(k, 0.5))
        except (TypeError, ValueError):
            out[f"ctx_{k}"] = 0.5
    return out
