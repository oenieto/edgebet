import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env


SYSTEM_PROMPT = """Eres el motor de análisis de Edgebet, una plataforma premium de predicciones de fútbol.

Tu rol: sintetizar datos cuantitativos de tres fuentes (modelo ML, Polymarket, cuotas Bet365) y generar análisis claros, honestos y accionables para apostadores en español.

Para cada pick, siempre incluye:
1. Predicción principal (outcome más probable)
2. Nivel de confianza (0-100%) con justificación breve
3. Análisis de divergencia: ¿coinciden las 3 fuentes? Si divergen, explica por qué puede ser relevante
4. Máximo 3 factores clave que sustentan la predicción
5. Máximo 2 riesgos principales
6. Stake sugerido basado en Kelly simplificado (% del bankroll)

Reglas:
- Sé directo y concreto. Sin relleno ni frases de relleno.
- Si la confianza es baja (<55%), dilo explícitamente
- Nunca garantices resultados
- Máximo 120 palabras de análisis
- Responde siempre en español
- Cuando se pida JSON, responde SOLO JSON válido sin markdown"""


def analyze_match(
    home_team: str,
    away_team: str,
    league: str,
    home_form: dict,
    away_form: dict,
    ml_probs: dict,
    bookmaker_probs: dict,
    polymarket_probs: dict | None = None,
    poly_liquidity: float = 0,
    poly_volume_24h: float = 0,
) -> dict:
    """
    Generate full pick analysis using Claude.
    Returns structured dict with prediction, confidence, reasoning.
    """
    poly_section = ""
    if polymarket_probs:
        poly_section = f"""
Polymarket:
- Home: {polymarket_probs.get('home', 'N/A'):.1%}
- Draw: {polymarket_probs.get('draw', 'N/A'):.1%}
- Away: {polymarket_probs.get('away', 'N/A'):.1%}
- Liquidez: ${poly_liquidity:,.0f} | Volumen 24h: ${poly_volume_24h:,.0f}"""

    prompt = f"""Analiza este partido y devuelve SOLO JSON válido (sin markdown):

Partido: {home_team} vs {away_team} ({league})

Probabilidades modelo ML:
- Local gana: {ml_probs.get('home', 0):.1%}
- Empate: {ml_probs.get('draw', 0):.1%}
- Visitante gana: {ml_probs.get('away', 0):.1%}

Bet365 (normalizado):
- Local: {bookmaker_probs.get('home', 0):.1%}
- Empate: {bookmaker_probs.get('draw', 0):.1%}
- Visitante: {bookmaker_probs.get('away', 0):.1%}
{poly_section}

Stats {home_team} (últimos 5):
- Goles marcados avg: {home_form.get('avg_GF', 0):.2f}
- Goles recibidos avg: {home_form.get('avg_GA', 0):.2f}
- Tiros al arco avg: {home_form.get('avg_SoT', 0):.1f}
- Forma (pts avg): {home_form.get('Form', 0):.2f}

Stats {away_team} (últimos 5):
- Goles marcados avg: {away_form.get('avg_GF', 0):.2f}
- Goles recibidos avg: {away_form.get('avg_GA', 0):.2f}
- Tiros al arco avg: {away_form.get('avg_SoT', 0):.1f}
- Forma (pts avg): {away_form.get('Form', 0):.2f}

Devuelve este JSON exacto:
{{
    "prediction": "home|draw|away",
    "confidence": ,
    "reasoning": "",
    "key_factors": ["factor1", "factor2", "factor3"],
    "risks": ["riesgo1", "riesgo2"],
    "suggested_stake_pct": ,
    "divergence_flag": ,
    "divergence_note": ""
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(response_text[start:end])
        return {"error": "Failed to parse response", "raw": response_text}


def analyze_matchday(matches: list[dict]) -> str:
    """Analyze full matchday with a single Claude call."""
    matches_text = ""
    for i, m in enumerate(matches, 1):
        matches_text += f"\n{i}. {m['home']} vs {m['away']}\n"
        matches_text += f"   ML: H={m['prob_H']:.0%} D={m['prob_D']:.0%} A={m['prob_A']:.0%}\n"
        matches_text += f"   Forma local: {m['home_form']:.2f} | Forma visitante: {m['away_form']:.2f}\n"

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"""Analiza la jornada completa. Para cada partido:
- Predicción (1X2)
- Confianza (⭐ baja, ⭐⭐ media, ⭐⭐⭐ alta)
- Comentario de 1 frase

Partidos:
{matches_text}

Al final: los 2 mejores picks de la jornada con mayor confianza."""}],
    )
    return message.content[0].text