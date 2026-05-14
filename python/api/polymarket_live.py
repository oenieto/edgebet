"""
Integración con Polymarket Gamma API para extraer liquidez y probabilidades implícitas
de los libros de órdenes en blockchain Polygon.

Robustez:
  - Circuit breaker simple: tras N fallos consecutivos abre el circuito por X minutos.
    Mientras está abierto, devolvemos None sin tocar la red. Esto evita amplificar
    timeouts hacia el endpoint /picks/today cuando la red está degradada.
  - Manejo granular de excepciones (Timeout, ConnectionError, HTTPError, JSONDecodeError, KeyError).
  - Logs estructurados con prefijo [polymarket] para grep en producción.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

import requests

GAMMA_URL = "https://gamma-api.polymarket.com"

# Circuit breaker — abre tras 5 fallos consecutivos, cierra después de 120s
_CB_FAIL_THRESHOLD = 5
_CB_OPEN_SECONDS = 120
_REQUEST_TIMEOUT = 5

logger = logging.getLogger("edgebet.polymarket")


class _CircuitBreaker:
    """Single-instance breaker — comparte estado entre todos los callers del proceso."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def can_request(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if (time.time() - self._opened_at) >= _CB_OPEN_SECONDS:
                # Half-open: cerramos para que el próximo intento decida.
                logger.info("[polymarket] circuit breaker half-open, intentando reset")
                self._opened_at = None
                self._consecutive_failures = 0
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            if self._consecutive_failures > 0:
                logger.info("[polymarket] recuperación tras %d fallo(s)", self._consecutive_failures)
            self._consecutive_failures = 0
            self._opened_at = None

    def record_failure(self, reason: str) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= _CB_FAIL_THRESHOLD:
                if self._opened_at is None:
                    self._opened_at = time.time()
                    logger.warning(
                        "[polymarket] circuit breaker ABIERTO tras %d fallos. Última causa: %s. "
                        "Pausando llamadas %ds.",
                        self._consecutive_failures, reason, _CB_OPEN_SECONDS,
                    )


_breaker = _CircuitBreaker()


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
    Devuelve None si no hay mercado, si la red falla, o si el breaker está abierto.
    """
    if not _breaker.can_request():
        return None

    search_q = f"{home_team} {away_team}"

    try:
        resp = requests.get(
            f"{GAMMA_URL}/events",
            params={"q": search_q, "active": "true"},
            timeout=_REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        logger.warning("[polymarket] timeout (%ds) buscando '%s'", _REQUEST_TIMEOUT, search_q)
        _breaker.record_failure("timeout")
        return None
    except requests.exceptions.ConnectionError as exc:
        logger.warning("[polymarket] ConnectionError para '%s': %s", search_q, exc)
        _breaker.record_failure("connection")
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("[polymarket] RequestException inesperada: %s", exc)
        _breaker.record_failure(f"request:{type(exc).__name__}")
        return None

    if resp.status_code != 200:
        logger.warning(
            "[polymarket] status=%d para '%s' — body[:200]=%r",
            resp.status_code, search_q, resp.text[:200],
        )
        # 4xx no es fallo de red — no abre circuito (puede ser query inválida).
        # 5xx sí cuenta como fallo de upstream.
        if 500 <= resp.status_code < 600:
            _breaker.record_failure(f"http_{resp.status_code}")
        return None

    try:
        data = resp.json()
    except ValueError as exc:
        logger.warning("[polymarket] respuesta no es JSON válido: %s", exc)
        _breaker.record_failure("json_decode")
        return None

    if not data:
        # No hay evento — la query falló pero la API funciona. No es un fallo.
        _breaker.record_success()
        return None

    try:
        event = data[0]
        markets = event.get("markets", [])
        match_market = next(
            (
                m for m in markets
                if "winner" in m.get("question", "").lower()
                or "win" in m.get("groupItemTitle", "").lower()
            ),
            None,
        )
        if not match_market:
            _breaker.record_success()
            return None

        prices_raw = match_market.get("outcomePrices", "[]")
        try:
            prices = json.loads(prices_raw)
        except (ValueError, TypeError) as exc:
            logger.warning("[polymarket] outcomePrices no parseable: %s — raw=%r", exc, prices_raw)
            _breaker.record_success()  # data malformada no es fallo de red
            return None

        if not prices or len(prices) < 2:
            _breaker.record_success()
            return None

        try:
            home_prob = float(prices[0])
            away_prob = float(prices[1])
            draw_prob = float(prices[2]) if len(prices) > 2 else max(0.0, 1.0 - home_prob - away_prob)
        except (ValueError, TypeError, IndexError) as exc:
            logger.warning("[polymarket] precios no numéricos: %s — raw=%r", exc, prices)
            _breaker.record_success()
            return None

        total = home_prob + away_prob + draw_prob
        if total <= 0:
            _breaker.record_success()
            return None

        liquidity = float(match_market.get("liquidity", 0) or 0)
        volume_24h = float(match_market.get("volume24hr", 0) or 0)

        _breaker.record_success()
        return PolyPick(
            home=home_prob / total,
            draw=draw_prob / total,
            away=away_prob / total,
            liquidity=liquidity,
            volume_24h=volume_24h,
            market_slug=event.get("slug", ""),
            confidence=0.9 if liquidity > 10_000 else 0.5,
        )
    except (KeyError, IndexError, TypeError) as exc:
        # Estructura inesperada de la respuesta — puede pasar si Gamma cambia el schema.
        logger.warning(
            "[polymarket] estructura inesperada para '%s': %s", search_q, exc,
        )
        _breaker.record_success()  # API funciona, pero schema cambió
        return None
    except Exception as exc:
        logger.exception("[polymarket] error inesperado: %s", exc)
        _breaker.record_failure(f"unknown:{type(exc).__name__}")
        return None


def breaker_state() -> dict:
    """Útil para /health endpoint."""
    return {
        "open": _breaker._opened_at is not None,
        "consecutive_failures": _breaker._consecutive_failures,
        "opened_at": _breaker._opened_at,
    }
