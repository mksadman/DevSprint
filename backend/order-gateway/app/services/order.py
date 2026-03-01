import logging
import threading
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Circuit Breaker ────────────────────────────────────────────────────────


class _CircuitBreaker:
    """
    Three-state circuit breaker: CLOSED → OPEN → HALF_OPEN → CLOSED.

    While OPEN, requests are rejected immediately without hitting the
    downstream service, preventing cascade failures.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self._lock = threading.Lock()
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failures = 0
        self._state = "CLOSED"
        self._opened_at = 0.0

    # -- state transitions ---------------------------------------------------

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = "CLOSED"

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._failure_threshold:
                self._state = "OPEN"
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit breaker OPEN after %d failures (recovery in %ds)",
                    self._failures, self._recovery_timeout,
                )

    def allow_request(self) -> bool:
        with self._lock:
            if self._state == "CLOSED":
                return True
            if self._state == "OPEN":
                if time.monotonic() - self._opened_at >= self._recovery_timeout:
                    self._state = "HALF_OPEN"
                    logger.info("Circuit breaker HALF_OPEN — allowing probe request")
                    return True
                return False
            # HALF_OPEN — allow one probe request
            return True

    @property
    def state(self) -> str:
        with self._lock:
            if (
                self._state == "OPEN"
                and time.monotonic() - self._opened_at >= self._recovery_timeout
            ):
                self._state = "HALF_OPEN"
            return self._state


_breaker = _CircuitBreaker(failure_threshold=5, recovery_timeout=30)


# ── HTTP client ────────────────────────────────────────────────────────────


def _timeout() -> httpx.Timeout:
    seconds = settings.GATEWAY_TIMEOUT_MS / 1000.0
    return httpx.Timeout(seconds)


# Shared connection-pool client — created lazily, reused across requests.
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=_timeout(),
            headers={"X-Internal-Key": settings.INTERNAL_API_KEY},
        )
    return _client


async def close_http_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
    _client = None


async def deduct_stock(order_id: str, item_id: str, quantity: int) -> dict[str, Any]:
    """
    Call stock-service to atomically verify and decrement stock.

    The circuit breaker rejects requests immediately when the downstream
    service has been failing, preventing connection-pool exhaustion.

    Raises:
        httpx.HTTPStatusError  — for any 4xx / 5xx response from stock-service.
        httpx.TimeoutException — when the call exceeds GATEWAY_TIMEOUT_MS.
        httpx.ConnectError     — when the circuit breaker is OPEN.
    """
    if not _breaker.allow_request():
        raise httpx.ConnectError("Circuit breaker OPEN — stock service unavailable")

    url = f"{settings.STOCK_SERVICE_URL.rstrip('/')}/stock/deduct"
    payload = {"order_id": order_id, "item_id": item_id, "quantity": quantity}

    try:
        client = _get_client()
        response = await client.post(url, json=payload)
        response.raise_for_status()
        _breaker.record_success()
        return response.json()
    except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
        _breaker.record_failure()
        raise
    except httpx.HTTPStatusError as exc:
        # Only trip the breaker on server errors (5xx), not client errors (4xx)
        if exc.response.status_code >= 500:
            _breaker.record_failure()
        else:
            _breaker.record_success()
        raise


async def stock_health_ping() -> bool:
    """Return ``True`` if stock-service /health responds with a non-5xx status."""
    url = f"{settings.STOCK_SERVICE_URL.rstrip('/')}/health"
    try:
        client = _get_client()
        resp = await client.get(url)
        return resp.status_code < 500
    except Exception:
        return False
