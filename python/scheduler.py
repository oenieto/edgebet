import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from data.snapshot_pipeline import run_snapshot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_scheduler():
    """
    Inicia el scheduler que ejecutará el pipeline de cuotas cada 4 horas.
    """
    logger.info("Iniciando APScheduler. El proceso de snapshot de The Odds API se ejecutará cada 4 horas.")
    scheduler = BlockingScheduler()
    
    # Añadimos el trabajo para que corra exactamente cada 4 horas
    scheduler.add_job(run_snapshot, 'interval', hours=4, id='odds_snapshot_job')
    
    # Ejecutar inmediatamente la primera vez para asegurar que tenemos datos de inicio
    logger.info("Ejecutando el primer snapshot de inmediato...")
    try:
        run_snapshot()
    except Exception as e:
        logger.error(f"Fallo durante el snapshot inicial: {e}")
        
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("APScheduler detenido.")

if __name__ == "__main__":
    start_scheduler()
