import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


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

    Returns:
        Parsed JSON response body on success (HTTP 2xx).

    Raises:
        httpx.HTTPStatusError  — for any 4xx / 5xx response from stock-service.
        httpx.TimeoutException — when the call exceeds GATEWAY_TIMEOUT_MS.
    """
    url = f"{settings.STOCK_SERVICE_URL.rstrip('/')}/stock/deduct"
    payload = {"order_id": order_id, "item_id": item_id, "quantity": quantity}

    client = _get_client()
    response = await client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


async def stock_health_ping() -> bool:
    """Return ``True`` if stock-service /health responds with a non-5xx status."""
    url = f"{settings.STOCK_SERVICE_URL.rstrip('/')}/health"
    try:
        client = _get_client()
        resp = await client.get(url)
        return resp.status_code < 500
    except Exception:
        return False
