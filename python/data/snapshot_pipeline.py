"""
Edgebet — job de snapshot de cuotas.

Usa el proveedor canónico `api.odds_provider` (single source of truth: lee
EDGEBET_ODDS_API_KEY y cachea en disco). `fetch_league_odds()` ya persiste
cada fixture con cuotas en `odds_snapshots`, así que este job solo orquesta el
barrido por liga y, de paso, refresca la tabla `fixtures` para que settlement
tenga partidos terminados que liquidar.

Reemplaza al antiguo `OddsProvider` basado en Redis (eliminado en el overhaul):
Redis no está desplegado y el cache en disco cubre el caso de uso del tier free.
"""
import logging
from datetime import datetime

from api.odds_provider import SPORT_KEY_BY_LEAGUE, fetch_league_odds, is_configured
from api.openfootball_loader import upsert_fixtures

logger = logging.getLogger(__name__)


def run_snapshot() -> dict:
    """
    Barre todas las ligas soportadas, persiste snapshots de cuotas y refresca
    la tabla `fixtures`. Devuelve un resumen serializable.
    """
    logger.info("Iniciando snapshot de cuotas a las %s", datetime.now().isoformat())

    if not is_configured():
        logger.warning("EDGEBET_ODDS_API_KEY no configurada — se omite el snapshot de cuotas.")
        fixtures_upserted = _refresh_fixtures()
        return {"leagues": 0, "fixtures_with_odds": 0, "fixtures_upserted": fixtures_upserted}

    leagues_done = 0
    fixtures_with_odds = 0
    for slug in SPORT_KEY_BY_LEAGUE:
        try:
            odds = fetch_league_odds(slug)  # persiste odds_snapshots internamente
        except Exception as exc:
            logger.warning("[snapshot] %s falló: %s", slug, exc)
            continue
        leagues_done += 1
        fixtures_with_odds += len(odds)
        logger.info("[snapshot] %s — %d fixtures con cuotas", slug, len(odds))

    # Mantener `fixtures` al día tras cada sync para que settle_pending_picks()
    # encuentre partidos status='finished'.
    fixtures_upserted = _refresh_fixtures()

    logger.info(
        "Snapshot completo: %d ligas, %d fixtures con cuotas, %d fixtures upserted.",
        leagues_done, fixtures_with_odds, fixtures_upserted,
    )
    return {
        "leagues": leagues_done,
        "fixtures_with_odds": fixtures_with_odds,
        "fixtures_upserted": fixtures_upserted,
    }


def _refresh_fixtures() -> int:
    try:
        return upsert_fixtures()
    except Exception as exc:
        logger.warning("[snapshot] upsert_fixtures falló: %s", exc)
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_snapshot()
