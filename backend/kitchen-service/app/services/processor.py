import asyncio
import logging
import random
import threading
import time
from typing import List
from uuid import UUID

from app.schemas.event import KitchenOrderEvent
from app.models.job import KitchenOrder

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_store: dict = {
    "total_orders_received": 0,
    "total_orders_processed": 0,
    "processing_times_ms": [],
}

_in_memory_queue: List[dict] = []


async def _notify_status(order_record: dict) -> None:
    """Publish status update to the kitchen_events RabbitMQ exchange."""
    try:
        from app.services.rabbitmq import publish_notification
        await publish_notification({
            "order_id": order_record["order_id"],
            "student_id": order_record["student_id"],
            "status": order_record["status"],
        })
    except Exception as exc:
        logger.warning("Notification push failed: %s", exc)


async def process_order_background(order_record: dict) -> None:
    """Simulate 3-7 s cooking time, cycling through QUEUED → IN_KITCHEN → READY."""
    cook_time = random.uniform(3.0, 7.0)
    start = time.monotonic()

    with _lock:
        order_record["status"] = "IN_KITCHEN"
    await _notify_status(order_record)

    await asyncio.sleep(cook_time)

    with _lock:
        order_record["status"] = "READY"
        elapsed_ms = (time.monotonic() - start) * 1000
        _store["total_orders_processed"] += 1
        _store["processing_times_ms"].append(elapsed_ms)
    await _notify_status(order_record)
    logger.info("Order %s READY in %.0f ms", order_record["order_id"], elapsed_ms)


def enqueue_order(event: KitchenOrderEvent) -> dict:
    """Accept an incoming order event and add it to the processing queue."""
    with _lock:
        _store["total_orders_received"] += 1
        order_record = {
            "order_id": str(event.order_id),
            "item_id": event.item_id,
            "quantity": event.quantity,
            "student_id": event.student_id,
            "status": "QUEUED",
        }
        _in_memory_queue.append(order_record)
        return order_record


def get_order_status(order_id: UUID) -> dict | None:
    """Return the current status record for an order, or None if not found."""
    order_id_str = str(order_id)
    with _lock:
        for order in _in_memory_queue:
            if order["order_id"] == order_id_str:
                return order
    return None


def get_metrics_snapshot() -> dict:
    """Return a point-in-time snapshot of processing counters."""
    with _lock:
        times = list(_store["processing_times_ms"])
        avg = sum(times) / len(times) if times else 0.0
        return {
            "total_orders_received": _store["total_orders_received"],
            "total_orders_processed": _store["total_orders_processed"],
            "average_processing_time_ms": round(avg, 3),
        }
