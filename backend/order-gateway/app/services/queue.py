"""
Transactional outbox for reliable order event delivery.

During order placement the event is written to the ``outbox_events`` table
in the **same** DB transaction as the order itself.  A background relay task
polls unpublished rows and publishes them to RabbitMQ, giving at-least-once
delivery with zero fire-and-forget message loss.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import aio_pika
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.outbox import OutboxEvent
from app.services.metrics import metrics

logger = logging.getLogger(__name__)

# Module-level connection / channel — initialised lazily.
_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None
_relay_task: asyncio.Task | None = None

EXCHANGE_NAME = "order_events"
ROUTING_KEY = "order.placed"
_RELAY_INTERVAL_SECONDS = 1
_RELAY_BATCH_SIZE = 50


# ── Outbox write — called INSIDE the caller's transaction ──────────────────


def publish_order_event(db: Session, event: dict[str, Any]) -> None:
    """
    Write an order event to the outbox table.

    Must be called **within** the caller's DB transaction (before commit).
    The background relay is responsible for actual RabbitMQ delivery.
    """
    outbox = OutboxEvent(
        aggregate_id=str(event.get("order_id", "")),
        event_type="order.placed",
        payload=event,
    )
    db.add(outbox)


# ── RabbitMQ connection management ─────────────────────────────────────────


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
    """Gracefully stop relay and close the RabbitMQ connection."""
    global _connection, _channel, _exchange, _relay_task
    if _relay_task is not None:
        _relay_task.cancel()
        try:
            await _relay_task
        except asyncio.CancelledError:
            pass
        _relay_task = None
    if _connection and not _connection.is_closed:
        await _connection.close()
    _connection = _channel = _exchange = None
    logger.info("RabbitMQ connection closed")


# ── Outbox relay (background task) ─────────────────────────────────────────


async def _relay_batch() -> int:
    """Publish one batch of pending outbox events.  Returns count published."""
    from app.core.database import SessionLocal

    if SessionLocal is None:
        return 0

    db = SessionLocal()
    try:
        pending = (
            db.query(OutboxEvent)
            .filter(OutboxEvent.published.is_(False))
            .order_by(OutboxEvent.created_at)
            .limit(_RELAY_BATCH_SIZE)
            .all()
        )
        if not pending:
            return 0

        exchange = await _ensure_channel()
        published = 0
        for event in pending:
            body = json.dumps(event.payload).encode()
            await exchange.publish(
                aio_pika.Message(
                    body=body,
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=ROUTING_KEY,
            )
            event.published = True
            event.published_at = datetime.now(timezone.utc)
            published += 1
        db.commit()
        if published:
            logger.info("Outbox relay published %d event(s)", published)
        return published
    except Exception as exc:
        db.rollback()
        metrics.increment_downstream_failures()
        logger.error("Outbox relay error: %s", exc)
        return 0
    finally:
        db.close()


async def _relay_loop() -> None:
    """Continuously poll the outbox and publish pending events to RabbitMQ."""
    while True:
        try:
            await _relay_batch()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Outbox relay loop error: %s", exc)
        await asyncio.sleep(_RELAY_INTERVAL_SECONDS)


def start_outbox_relay() -> None:
    """Launch the relay background task on the running event loop."""
    global _relay_task
    _relay_task = asyncio.create_task(_relay_loop())
    logger.info("Outbox relay started (interval=%ds)", _RELAY_INTERVAL_SECONDS)
