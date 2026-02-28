import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services.metrics import metrics

logger = logging.getLogger(__name__)


async def _publish(event: dict[str, Any]) -> None:
    """Internal coroutine — errors are absorbed so the caller is never affected."""
    url = f"{settings.KITCHEN_QUEUE_URL.rstrip('/')}/orders"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            response = await client.post(url, json=event)
            response.raise_for_status()
            logger.info(
                "Order event published to kitchen-service: order_id=%s",
                event.get("order_id"),
            )
    except Exception as exc:
        metrics.increment_downstream_failures()
        logger.error(
            "Failed to publish order event to kitchen-service: %s — order_id=%s",
            exc,
            event.get("order_id"),
        )


def publish_order_event(event: dict[str, Any]) -> None:
    """
    Fire-and-forget publish to kitchen-service.

    Schedules ``_publish`` on the running event loop without blocking the caller.
    Publish failures are logged and metered; they never roll back prior operations.
    """
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_publish(event))
    except RuntimeError as exc:
        metrics.increment_downstream_failures()
        logger.error("Could not schedule kitchen-service publish: %s", exc)
