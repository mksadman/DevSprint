"""
RabbitMQ consumer for the notification service.

Consumes from ``notification_queue`` bound to ``kitchen_events`` exchange
with routing key ``order.status``.  Each message is:
  - persisted to the ``notifications`` table
  - pushed to the matching student's WebSocket connection(s)
"""
import json
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.core.config import RABBITMQ_URL
from app.services.notifier import send_to_student

logger = logging.getLogger(__name__)

_connection: aio_pika.abc.AbstractConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None

EXCHANGE_NAME = "kitchen_events"
QUEUE_NAME = "notification_queue"
ROUTING_KEY = "order.status"

# Counter for metrics
_messages_consumed: int = 0
_notifications_persisted: int = 0


def get_messages_consumed() -> int:
    return _messages_consumed


def get_notifications_persisted() -> int:
    return _notifications_persisted


async def _on_message(message: AbstractIncomingMessage) -> None:
    """Process an incoming kitchen status event."""
    global _messages_consumed, _notifications_persisted
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            order_id = data.get("order_id", "")
            student_id = data.get("student_id", "")
            status = data.get("status", "")

            logger.info(
                "Consumed notification event: order_id=%s student=%s status=%s",
                order_id, student_id, status,
            )
            _messages_consumed += 1

            # Persist to DB
            try:
                from app.core.database import SessionLocal
                from app.models.connection import Notification
                db = SessionLocal()
                notif = Notification(
                    order_id=order_id,
                    student_id=student_id,
                    status_sent=status,
                )
                db.add(notif)
                db.commit()
                db.close()
                _notifications_persisted += 1
            except Exception as exc:
                logger.warning("Failed to persist notification: %s", exc)

            # Push to student's WebSocket connections
            ws_message = json.dumps({
                "event": "order_status",
                "payload": {
                    "order_id": order_id,
                    "student_id": student_id,
                    "status": status,
                },
            })
            await send_to_student(student_id, ws_message)

        except Exception as exc:
            logger.error("Failed to process notification message: %s", exc)


async def start_consumer() -> None:
    """Declare exchange, queue, binding and start consuming."""
    global _connection, _channel
    _connection = await aio_pika.connect(RABBITMQ_URL, timeout=5.0)
    _channel = await _connection.channel()
    await _channel.set_qos(prefetch_count=10)

    exchange = await _channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True,
    )
    queue = await _channel.declare_queue(QUEUE_NAME, durable=True)
    await queue.bind(exchange, routing_key=ROUTING_KEY)

    await queue.consume(_on_message)
    logger.info(
        "Notification RabbitMQ consumer started — queue=%s exchange=%s key=%s",
        QUEUE_NAME, EXCHANGE_NAME, ROUTING_KEY,
    )


async def close_rabbitmq() -> None:
    """Gracefully close the RabbitMQ connection."""
    global _connection, _channel
    if _connection and not _connection.is_closed:
        await _connection.close()
    _connection = _channel = None
    logger.info("Notification RabbitMQ connection closed")


async def check_rabbitmq_health() -> bool:
    """Return True if the RabbitMQ connection is alive."""
    return _connection is not None and not _connection.is_closed
