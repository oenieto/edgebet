"""
Integración con Polymarket Gamma API para extraer liquidez y probabilidades implícitas
de los libros de órdenes en blockchain Polygon.
"""
from __future__ import annotations

import requests
from dataclasses import dataclass
from typing import Optional

# Gamma API base (pública, sin auth necesaria para lectura de markets/events)
GAMMA_URL = "https://gamma-api.polymarket.com"

@dataclass
class PolyPick:
    home: float
    draw: float
    away: float
    liquidity: float
    volume_24h: float
    market_slug: str
    confidence: float

def find_match_probs(home_team: str, away_team: str) -> Optional[PolyPick]:
    """
    Busca el evento en Polymarket y devuelve las probabilidades implied.
    Debido a que Gamma API indexa por slugs, construimos slugs posibles y buscamos.
    """
    search_q = f"{home_team} {away_team}"
    
    try:
        # 1. Buscar evento
        resp = requests.get(f"{GAMMA_URL}/events", params={"q": search_q, "active": "true"}, timeout=3)
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        if not data:
            return None
            
        event = data[0] # Tomamos el más relevante
        markets = event.get("markets", [])
        
        # Filtramos por mercado de 'ganador del partido' (1x2)
        match_market = next(
            (m for m in markets if "winner" in m.get("question", "").lower() or "win" in m.get("groupItemTitle", "").lower()), 
            None
        )
        if not match_market:
            return None
            
        # Parse outputcomes (puede ser binario o 3-way)
        outcomes = match_market.get("outcomes", [])
        prices = json.loads(match_market.get("outcomePrices", "[]"))
        
        if not prices or len(prices) < 2:
            return None
            
        # Simplificación: mapeo posicional asumiendo Home, Away, Draw en outcomes
        # Para robustez en pro, se requiere fuzzy matching de los nombres en outcomes
        home_prob = float(prices[0])
        away_prob = float(prices[1])
        draw_prob = float(prices[2]) if len(prices) > 2 else (1.0 - home_prob - away_prob)
        
        # Normalizar
        total = home_prob + away_prob + draw_prob
        
        return PolyPick(
            home=home_prob / total,
            draw=draw_prob / total,
            away=away_prob / total,
            liquidity=float(match_market.get("liquidity", 0)),
            volume_24h=float(match_market.get("volume24hr", 0)),
            market_slug=event.get("slug", ""),
            confidence=0.9 if float(match_market.get("liquidity", 0)) > 10000 else 0.5
        )
    except Exception as e:
        print(f"[gamma_api] Error consultando polymarket: {e}")
        return None
