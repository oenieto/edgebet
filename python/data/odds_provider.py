import os
import json
import logging
import requests
import redis
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OddsProvider:
    """
    Client for The Odds API using Redis for cache-aside to avoid 
    exhausting the rate limits of the $30/mo plan.
    """
    
    BASE_URL = "https://api.the-odds-api.com/v4/sports"
    
    def __init__(self):
        self.api_key = os.getenv("ODDS_API_KEY")
        if not self.api_key:
            logger.warning("ODDS_API_KEY no está configurada en las variables de entorno.")
            
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
        except redis.ConnectionError as e:
            logger.error(f"No se pudo conectar a Redis: {e}")
            self.redis_client = None

    def get_odds(self, sport: str, regions: str = "eu,uk", markets: str = "h2h,spreads,totals", cache_ttl: int = 3600) -> Optional[list]:
        """
        Retrieves odds for a specific sport.
        Uses Cache-aside: checks Redis first. If not found, fetches from API and stores in Redis.
        """
        cache_key = f"odds_provider:odds:{sport}:{regions}:{markets}"
        
        # 1. Cache-aside: Check Redis
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    logger.info(f"Cache hit para {sport} ({regions}, {markets})")
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"Error al leer de Redis: {e}")
                
        # 2. Fetch from API if not in cache or Redis failed
        if not self.api_key:
            logger.error("No se puede hacer fetch a The Odds API: API Key faltante.")
            return None
            
        url = f"{self.BASE_URL}/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": "decimal"
        }
        
        try:
            logger.info(f"Haciendo fetch a The Odds API para {sport}...")
            response = requests.get(url, params=params, timeout=15)
            
            # Rate limiting / Plan limits check
            requests_remaining = response.headers.get('x-requests-remaining')
            requests_used = response.headers.get('x-requests-used')
            if requests_remaining:
                logger.info(f"The Odds API quota: {requests_remaining} remaining, {requests_used} used.")
                
            if response.status_code == 429:
                logger.error("Rate limit excedido (429) de The Odds API.")
                return None
                
            response.raise_for_status()
            data = response.json()
            
            # 3. Store in cache
            if self.redis_client and data:
                try:
                    self.redis_client.setex(cache_key, cache_ttl, json.dumps(data))
                except Exception as e:
                    logger.error(f"Error al escribir en Redis: {e}")
                    
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la petición a The Odds API: {e}")
            return None
