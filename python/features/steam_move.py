import pandas as pd
from datetime import datetime, timedelta
import logging
from api.db import connect

logger = logging.getLogger(__name__)

def calculate_steam_move_24h() -> pd.DataFrame:
    """
    Calcula el 'steam move' (movimiento de cuota) comparando el valor actual
    con el de hace aproximadamente 24 horas para el mismo evento, bookmaker y mercado.
    
    Retorna un DataFrame de Pandas con la comparación (current_odd, past_odd, steam_move).
    """
    now = datetime.now()
    yesterday = now - timedelta(hours=24)
    
    # Definimos un margen de +/- 2 horas para encontrar el snapshot de ayer
    window_start = yesterday - timedelta(hours=2)
    window_end = yesterday + timedelta(hours=2)
    
    # current_odds tomará lo de las últimas 4 horas
    query = """
    WITH current_odds AS (
        SELECT event_id, bookmaker, market, odds_value AS current_odd
        FROM odds_history
        WHERE timestamp >= %s
    ),
    past_odds AS (
        SELECT event_id, bookmaker, market, odds_value AS past_odd
        FROM odds_history
        WHERE timestamp BETWEEN %s AND %s
    )
    SELECT 
        c.event_id, 
        c.bookmaker, 
        c.market, 
        c.current_odd, 
        p.past_odd,
        (c.current_odd - p.past_odd) AS steam_move
    FROM current_odds c
    JOIN past_odds p 
      ON c.event_id = p.event_id 
     AND c.bookmaker = p.bookmaker 
     AND c.market = p.market;
    """
    
    try:
        with connect() as cur:
            cur.execute(query, (now - timedelta(hours=4), window_start, window_end))
            records = cur.fetchall()
            
            df = pd.DataFrame(records, columns=[
                'event_id', 'bookmaker', 'market', 'current_odd', 'past_odd', 'steam_move'
            ])
            
            # Limpiamos duplicados si hay múltiples snapshots en el mismo rango de tiempo
            df = df.drop_duplicates(subset=['event_id', 'bookmaker', 'market'], keep='last')
            
            logger.info(f"Calculados {len(df)} registros de steam move.")
            return df
            
    except Exception as e:
        logger.error(f"Error al calcular steam move 24h: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df_steam = calculate_steam_move_24h()
    if not df_steam.empty:
        print(df_steam.head())
    else:
        print("No hay datos para calcular steam move o la tabla está vacía.")
