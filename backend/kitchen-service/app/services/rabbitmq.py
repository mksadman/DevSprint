"""
RabbitMQ consumer (order_events) and publisher (kitchen_events) for
the kitchen service.

Consumer:  binds ``kitchen_queue`` to ``order_events`` with key ``order.placed``
Publisher: publishes to ``kitchen_events`` with key ``order.status``
"""
import asyncio
import json
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.core.config import RABBITMQ_URL
from app.schemas.event import KitchenOrderEvent
from app.services.processor import enqueue_order, process_order_background

logger = logging.getLogger(__name__)

# ── Module-level connection state ───────────────────────────────────────────
_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None
_publish_exchange: aio_pika.abc.AbstractExchange | None = None

ORDER_EXCHANGE = "order_events"
KITCHEN_EXCHANGE = "kitchen_events"
QUEUE_NAME = "kitchen_queue"
CONSUME_KEY = "order.placed"
PUBLISH_KEY = "order.status"


# ── Publisher ───────────────────────────────────────────────────────────────
async def _ensure_publish_exchange() -> aio_pika.abc.AbstractExchange:
    """Return (or create) the ``kitchen_events`` topic exchange."""
    global _publish_exchange
    if _publish_exchange is not None:
        return _publish_exchange

    channel = await _get_channel()
    _publish_exchange = await channel.declare_exchange(
        KITCHEN_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True,
    )
    return _publish_exchange


async def publish_notification(payload: dict) -> None:
    """Publish a status event to the ``kitchen_events`` exchange."""
    try:
        exchange = await _ensure_publish_exchange()
        body = json.dumps(payload).encode()
        await exchange.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=PUBLISH_KEY,
        )
        logger.info(
            "Status event published to RabbitMQ: order_id=%s status=%s",
            payload.get("order_id"),
            payload.get("status"),
        )
    except Exception as exc:
        logger.warning("Failed to publish status event to RabbitMQ: %s", exc)


# ── Consumer ────────────────────────────────────────────────────────────────
async def _get_channel() -> aio_pika.abc.AbstractChannel:
    global _connection, _channel
    if _channel is not None and _connection is not None and not _connection.is_closed:
        return _channel
    _connection = await aio_pika.connect(RABBITMQ_URL, timeout=5.0)
    _channel = await _connection.channel()
    await _channel.set_qos(prefetch_count=10)
    return _channel


async def _on_message(message: AbstractIncomingMessage) -> None:
    """Callback invoked for every message on ``kitchen_queue``."""
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            event = KitchenOrderEvent(**data)
            record = enqueue_order(event)
            asyncio.create_task(process_order_background(record))
            logger.info("Order consumed from RabbitMQ: order_id=%s", data.get("order_id"))
        except Exception as exc:
            logger.error("Failed to process RabbitMQ message: %s", exc)


async def start_consumer() -> None:
    """Declare exchange, queue, binding and start consuming."""
    channel = await _get_channel()

    exchange = await channel.declare_exchange(
        ORDER_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True,
    )
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    await queue.bind(exchange, routing_key=CONSUME_KEY)

    await queue.consume(_on_message)
    logger.info(
        "Kitchen RabbitMQ consumer started — queue=%s exchange=%s key=%s",
        QUEUE_NAME, ORDER_EXCHANGE, CONSUME_KEY,
    )


async def close_rabbitmq() -> None:
    """Gracefully close the RabbitMQ connection."""
    global _connection, _channel, _publish_exchange
    if _connection and not _connection.is_closed:
        await _connection.close()
    _connection = _channel = _publish_exchange = None
    logger.info("Kitchen RabbitMQ connection closed")
