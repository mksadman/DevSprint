import asyncio
import logging
import random
import threading
import time
from collections import deque
from typing import List
from uuid import UUID

from app.schemas.event import KitchenOrderEvent
from app.models.job import KitchenOrder

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_store: dict = {
    "total_orders_received": 0,
    "total_orders_processed": 0,
    "processing_times_ms": deque(maxlen=10_000),
}

_in_memory_queue: List[dict] = []
_seen_order_ids: set = set()


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


def _persist_order(order_record: dict, status: str, **extra_fields) -> None:
    """Write or update a KitchenOrder row in the database (best-effort)."""
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            existing = (
                db.query(KitchenOrder)
                .filter(KitchenOrder.order_id == order_record["order_id"])
                .first()
            )
            if existing:
                existing.status = status
                for k, v in extra_fields.items():
                    setattr(existing, k, v)
            else:
                row = KitchenOrder(
                    order_id=order_record["order_id"],
                    status=status,
                )
                for k, v in extra_fields.items():
                    setattr(row, k, v)
                db.add(row)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Failed to persist kitchen order: %s", exc)


async def process_order_background(order_record: dict) -> None:
    """Simulate 3-7 s cooking time, cycling through QUEUED → IN_KITCHEN → READY."""
    cook_time = random.uniform(3.0, 7.0)
    start = time.monotonic()

    with _lock:
        order_record["status"] = "IN_KITCHEN"

    from datetime import datetime, timezone
    _persist_order(order_record, "IN_KITCHEN", started_at=datetime.now(timezone.utc))
    await _notify_status(order_record)

    await asyncio.sleep(cook_time)

    with _lock:
        order_record["status"] = "READY"
        elapsed_ms = (time.monotonic() - start) * 1000
        _store["total_orders_processed"] += 1
        _store["processing_times_ms"].append(elapsed_ms)

    _persist_order(order_record, "READY", completed_at=datetime.now(timezone.utc))
    await _notify_status(order_record)
    logger.info("Order %s READY in %.0f ms", order_record["order_id"], elapsed_ms)


def enqueue_order(event: KitchenOrderEvent) -> dict:
    """Accept an incoming order event and add it to the processing queue.

    Returns existing record if order_id was already enqueued (idempotent).
    """
    order_id_str = str(event.order_id)
    with _lock:
        # Idempotency: skip if already seen
        if order_id_str in _seen_order_ids:
            for order in _in_memory_queue:
                if order["order_id"] == order_id_str:
                    logger.info("Duplicate order_id=%s — skipping", order_id_str)
                    return order
            # Fallback: in set but not in queue (shouldn't happen)
            logger.warning("order_id=%s in seen set but not in queue", order_id_str)

        _store["total_orders_received"] += 1
        order_record = {
            "order_id": order_id_str,
            "item_id": event.item_id,
            "quantity": event.quantity,
            "student_id": event.student_id,
            "status": "QUEUED",
        }
        _in_memory_queue.append(order_record)
        _seen_order_ids.add(order_id_str)

    # Persist to DB (best-effort, outside lock)
    _persist_order(order_record, "QUEUED")
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
