import logging
import sys
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from data.snapshot_pipeline import run_snapshot

# Permitir imports desde python/
_PY_ROOT = Path(__file__).resolve().parent
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from api.picks_service import generate_and_persist_picks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_scheduler():
    """
    Inicia el scheduler: snapshots de cuotas cada 4 horas y generación diaria
    de picks a las 06:00 UTC (tras la publicación de alineaciones en Europa).
    """
    logger.info("Iniciando APScheduler. Snapshots cada 4h; generación de picks diaria 06:00 UTC.")
    scheduler = BlockingScheduler(timezone="UTC")

    # Snapshot de cuotas cada 4 horas.
    scheduler.add_job(run_snapshot, 'interval', hours=4, id='odds_snapshot_job')

    # Generación + persistencia de picks una vez al día, 06:00 UTC.
    scheduler.add_job(
        generate_and_persist_picks, 'cron', hour=6, minute=0,
        id='daily_picks_job', timezone="UTC",
    )

    # Ejecutar inmediatamente la primera vez para asegurar que tenemos datos de inicio
    logger.info("Ejecutando el primer snapshot de inmediato...")
    try:
        run_snapshot()
    except Exception as e:
        logger.error(f"Fallo durante el snapshot inicial: {e}")

    logger.info("Ejecutando generación inicial de picks...")
    try:
        generate_and_persist_picks()
    except Exception as e:
        logger.error(f"Fallo durante la generación inicial de picks: {e}")
        
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("APScheduler detenido.")

if __name__ == "__main__":
    start_scheduler()
