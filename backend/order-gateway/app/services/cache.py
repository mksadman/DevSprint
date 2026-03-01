import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_STOCK_KEY_PREFIX = "stock:"
_CACHE_TTL_SECONDS = 60


def _make_key(item_id: str) -> str:
    return f"{_STOCK_KEY_PREFIX}{item_id}"


def _get_client() -> aioredis.Redis:
    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


async def get_cached_stock(item_id: str) -> Optional[int]:
    """
    Return the cached stock level for *item_id*, or ``None`` when:
      - The key does not exist in Redis.
      - Redis is unavailable (failure is logged, not raised).
    """
    try:
        async with _get_client() as client:
            value = await client.get(_make_key(item_id))
            if value is None:
                return None
            return int(value)
    except Exception as exc:
        logger.warning("Redis read failed for item '%s': %s", item_id, exc)
        return None


async def set_cached_stock(item_id: str, quantity: int) -> None:
    """
    Write the stock level for *item_id* to Redis with a TTL.
    Failures are logged and swallowed — never propagated to callers.
    """
    try:
        async with _get_client() as client:
            await client.set(_make_key(item_id), quantity, ex=_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Redis write failed for item '%s': %s", item_id, exc)


async def redis_ping() -> bool:
    """Return ``True`` if Redis is reachable, ``False`` otherwise."""
    try:
        async with _get_client() as client:
            return bool(await client.ping())
    except Exception:
        return False
