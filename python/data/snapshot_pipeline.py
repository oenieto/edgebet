import logging
from datetime import datetime
from api.db import connect
from data.odds_provider import OddsProvider
import psycopg2.extras

logger = logging.getLogger(__name__)

SPORTS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_italy_serie_a",
    "soccer_germany_bundesliga",
    "soccer_france_ligue_one",
    "soccer_portugal_primeira_liga",
    "soccer_uefa_champions_league",
    "soccer_fifa_world_cup"
]

def run_snapshot():
    """
    Fetches the latest odds for the configured sports and stores them in the database.
    """
    logger.info(f"Iniciando snapshot de cuotas a las {datetime.now()}")
    provider = OddsProvider()
    
    all_odds_records = []
    timestamp = datetime.now()
    
    for sport in SPORTS:
        logger.info(f"Obteniendo cuotas para {sport}...")
        data = provider.get_odds(sport)
        
        if not data:
            logger.warning(f"No se obtuvieron datos para {sport}.")
            continue
            
        # Parse and prepare data for bulk insert
        for event in data:
            event_id = event.get('id')
            bookmakers = event.get('bookmakers', [])
            
            for bookmaker in bookmakers:
                bookmaker_name = bookmaker.get('key')
                markets = bookmaker.get('markets', [])
                
                for market in markets:
                    market_name = market.get('key')
                    outcomes = market.get('outcomes', [])
                    
                    for outcome in outcomes:
                        # Para simplificar, guardamos el nombre del outcome como parte del market
                        # Ej: h2h_Arsenal, totals_Over_2.5
                        outcome_name = outcome.get('name')
                        price = outcome.get('price')
                        
                        full_market_name = f"{market_name}_{outcome_name}"
                        
                        all_odds_records.append((
                            timestamp,
                            event_id,
                            bookmaker_name,
                            full_market_name,
                            price
                        ))
                        
    if not all_odds_records:
        logger.info("No hay nuevas cuotas para insertar.")
        return
        
    # Bulk insert into odds_history
    try:
        with connect() as cur:
            insert_query = """
                INSERT INTO odds_history (timestamp, event_id, bookmaker, market, odds_value)
                VALUES %s
            """
            psycopg2.extras.execute_values(
                cur,
                insert_query,
                all_odds_records,
                page_size=1000
            )
            logger.info(f"Se insertaron {len(all_odds_records)} registros en odds_history exitosamente.")
    except Exception as e:
        logger.error(f"Error al insertar en la base de datos: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_snapshot()
