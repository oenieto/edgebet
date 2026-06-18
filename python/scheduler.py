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


from pathlib import Path as _Path
from datetime import datetime as _dt, timezone as _tz

_PIPELINE_LOG = _Path(__file__).resolve().parent / "data" / "pipeline_last_run.log"
# Ventana del Mundial 2026 (UTC): durante estas fechas el pipeline corre A DIARIO.
_WC_WINDOW = (_dt(2026, 6, 11, tzinfo=_tz.utc).date(), _dt(2026, 7, 19, tzinfo=_tz.utc).date())


def run_national_pipeline() -> dict:
    """Pipeline completo de selecciones: carga todas las fuentes, recomputa ELO,
    reajusta Poisson, refresca la cache del dashboard y escribe un log de la corrida.
    """
    from data.national_team_loader import load_all_sources
    from features.elo import load_national_team_history, compute_national_elo_from_history
    from api.poisson_predictor import get_national_predictor

    summary = {"rows": 0, "poisson": 0, "elo_fallback": 0, "by_source": {}, "errors": []}
    try:
        rows = load_all_sources(write=True)
        summary["rows"] = len(rows)
        for r in rows:
            s = r.get("source", "?")
            summary["by_source"][s] = summary["by_source"].get(s, 0) + 1

        df = load_national_team_history()
        compute_national_elo_from_history(df)  # recalibra ELO desde resultados reales
        predictor = get_national_predictor().fit_national_teams(df)

        # Cobertura Poisson sobre las 48 del Mundial.
        try:
            from api.world_cup import all_teams
            for t in all_teams():
                if predictor.has_team_data(t.key):
                    summary["poisson"] += 1
                else:
                    summary["elo_fallback"] += 1
        except Exception as exc:
            summary["errors"].append(f"coverage: {exc}")

        # Refrescar la cache del dashboard (mtime del CSV cambió → _ensure_model reajusta).
        try:
            import api.world_cup_router as wr
            wr._model_ready = False
        except Exception as exc:
            summary["errors"].append(f"cache: {exc}")
    except Exception as exc:
        summary["errors"].append(str(exc))
        logger.error("Pipeline de selecciones falló: %s", exc)

    _write_pipeline_log(summary)
    logger.info(
        "Pipeline selecciones: %d partidos · Poisson %d/48 · fallback %d/48",
        summary["rows"], summary["poisson"], summary["elo_fallback"],
    )
    return summary


def _write_pipeline_log(summary: dict) -> None:
    """Sobrescribe python/data/pipeline_last_run.log con el resultado de la corrida."""
    try:
        lines = [
            f"=== Edgebet national pipeline — {_dt.now(_tz.utc).isoformat()} ===",
            f"CSV rows:            {summary['rows']}",
            f"Poisson historical:  {summary['poisson']}/48",
            f"ELO fallback:        {summary['elo_fallback']}/48",
            "By source:",
        ]
        for s, n in sorted(summary["by_source"].items(), key=lambda kv: -kv[1]):
            lines.append(f"  {s:20s} {n}")
        lines.append("Errors / source failures:")
        lines.append("  " + ("; ".join(summary["errors"]) if summary["errors"] else "ninguno"))
        _PIPELINE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        logger.warning("No pude escribir %s: %s", _PIPELINE_LOG, exc)


def _wc_window_daily_pipeline() -> None:
    """Durante la ventana del Mundial corre el pipeline a diario; fuera, no-op."""
    today = _dt.now(_tz.utc).date()
    if _WC_WINDOW[0] <= today <= _WC_WINDOW[1]:
        logger.info("Ventana del Mundial activa — corrida diaria del pipeline.")
        run_national_pipeline()


def sync_wc_fixtures_job() -> None:
    """Sincroniza los fixtures del Mundial desde Odds API."""
    try:
        logger.info("[scheduler] Iniciando sync_wc_fixtures_job...")
        from data.wc_fixture_sync import sync_wc_fixtures_from_odds_api
        res = sync_wc_fixtures_from_odds_api()
        logger.info("[scheduler] sync_wc_fixtures_job finalizado: %s", res)
    except Exception as exc:
        logger.error("[scheduler] Error en sync_wc_fixtures_job: %s", exc)


def check_wc_live_scores_job() -> None:
    """Verifica resultados de partidos en vivo si el Mundial está activo."""
    today = _dt.now(_tz.utc).date()
    if _WC_WINDOW[0] <= today <= _WC_WINDOW[1]:
        try:
            logger.info("[scheduler] Verificando partidos en vivo del Mundial...")
            from data.wc_fixture_sync import check_live_wc_scores
            check_live_wc_scores()
        except Exception as exc:
            logger.error("[scheduler] Error en check_wc_live_scores_job: %s", exc)


def start_scheduler():
    """
    Inicia el scheduler: snapshots de cuotas cada 4 horas y generación diaria
    de picks a las 06:00 UTC (tras la publicación de alineaciones en Europa).
    """
    logger.info("Iniciando APScheduler. Snapshots cada 4h; generación de picks diaria 06:00 UTC.")
    scheduler = BlockingScheduler(timezone="UTC")

    # Snapshot de cuotas cada 4 horas.
    scheduler.add_job(run_snapshot, 'interval', hours=4, id='odds_snapshot_job')

    # Sincronización de fixtures de la Copa del Mundo cada 4 horas
    scheduler.add_job(sync_wc_fixtures_job, 'interval', hours=4, id='sync_wc_fixtures_job')

    # Verificación de partidos en vivo del Mundial cada 15 minutos
    scheduler.add_job(check_wc_live_scores_job, 'interval', minutes=15, id='check_wc_live_scores_job')

    # Generación + persistencia de picks una vez al día, 06:00 UTC.
    scheduler.add_job(
        generate_and_persist_picks, 'cron', hour=6, minute=0,
        id='daily_picks_job', timezone="UTC",
    )

    # Selecciones nacionales: pipeline completo (carga + ELO + Poisson + log) los
    # domingos 04:00 UTC. Durante la ventana del Mundial, además a diario 06:00 UTC.
    scheduler.add_job(
        run_national_pipeline, 'cron', day_of_week='sun', hour=4, minute=0,
        id='national_pipeline_weekly', timezone="UTC",
    )
    scheduler.add_job(
        _wc_window_daily_pipeline, 'cron', hour=6, minute=0,
        id='national_pipeline_wc_daily', timezone="UTC",
    )

    # Ejecutar inmediatamente la primera vez para asegurar que tenemos datos de inicio
    logger.info("Ejecutando el primer snapshot de inmediato...")
    try:
        run_snapshot()
    except Exception as e:
        logger.error(f"Fallo durante el snapshot inicial: {e}")

    logger.info("Ejecutando sincronización de Copa del Mundo inicial...")
    try:
        sync_wc_fixtures_job()
    except Exception as e:
        logger.error(f"Fallo durante la sincronización inicial de Copa del Mundo: {e}")

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
