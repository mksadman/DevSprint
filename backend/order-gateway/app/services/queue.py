"""
Fire-and-forget publisher that sends order events to a RabbitMQ exchange.

The kitchen-service consumes from the ``order_events`` exchange via the
``kitchen_queue`` queue bound with routing key ``order.placed``.
"""
import asyncio
import json
import logging
from typing import Any

import aio_pika

from app.core.config import settings
from app.services.metrics import metrics

logger = logging.getLogger(__name__)

# Module-level connection / channel — initialised lazily on first publish.
_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None

EXCHANGE_NAME = "order_events"
ROUTING_KEY = "order.placed"


async def _ensure_channel() -> aio_pika.abc.AbstractExchange:
    """Return (or create) a durable topic exchange on a persistent connection."""
    global _connection, _channel, _exchange

    if _exchange is not None and _connection is not None and not _connection.is_closed:
        return _exchange

    _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    _channel = await _connection.channel()
    _exchange = await _channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True,
    )
    logger.info("RabbitMQ exchange '%s' ready", EXCHANGE_NAME)
    return _exchange


async def close_rabbitmq() -> None:
    """Gracefully close the RabbitMQ connection (called on shutdown)."""
    global _connection, _channel, _exchange
    if _connection and not _connection.is_closed:
        await _connection.close()
    _connection = _channel = _exchange = None
    logger.info("RabbitMQ connection closed")


async def _publish(event: dict[str, Any]) -> None:
    """Internal coroutine — errors are absorbed so the caller is never affected."""
    try:
        exchange = await _ensure_channel()
        body = json.dumps(event).encode()
        await exchange.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=ROUTING_KEY,
        )
        logger.info(
            "Order event published to RabbitMQ: order_id=%s",
            event.get("order_id"),
        )
    except Exception as exc:
        metrics.increment_downstream_failures()
        logger.error(
            "Failed to publish order event to RabbitMQ: %s — order_id=%s",
            exc,
            event.get("order_id"),
        )


def publish_order_event(event: dict[str, Any]) -> None:
    """
    Fire-and-forget publish to RabbitMQ ``order_events`` exchange.

    Schedules ``_publish`` on the running event loop without blocking the caller.
    Publish failures are logged and metered; they never roll back prior operations.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_publish(event))
    except RuntimeError as exc:
        metrics.increment_downstream_failures()
        logger.error("Could not schedule RabbitMQ publish: %s", exc)
