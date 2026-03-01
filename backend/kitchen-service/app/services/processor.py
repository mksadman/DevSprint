import asyncio
import logging
import random
import threading
import time
from typing import List
from uuid import UUID

import httpx

from app.core.config import NOTIFICATION_SERVICE_URL
from app.schemas.event import KitchenOrderEvent

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_store: dict = {
    "total_orders_received": 0,
    "total_orders_processed": 0,
    "processing_times_ms": [],
}

_in_memory_queue: List[dict] = []


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


async def process_order_background(order_record: dict) -> None:
    """
    Background task: simulate cooking (3-7s).

    Transitions: QUEUED → IN_KITCHEN → READY
    Pushes status updates to the Notification Service at each transition.
    """
    start = time.perf_counter()
    order_id = order_record["order_id"]
    student_id = order_record["student_id"]

    # Small delay before kitchen picks up the order
    await asyncio.sleep(0.5)

    # Transition to IN_KITCHEN
    with _lock:
        order_record["status"] = "IN_KITCHEN"
    logger.info("Order %s → IN_KITCHEN", order_id)
    await _notify_status(order_id, student_id, "IN_KITCHEN")

    # Simulate cooking (3-7 seconds as per requirements)
    cook_time = random.uniform(3, 7)
    await asyncio.sleep(cook_time)

    # Transition to READY
    with _lock:
        order_record["status"] = "READY"
        _store["total_orders_processed"] += 1
        elapsed = (time.perf_counter() - start) * 1000
        _store["processing_times_ms"].append(elapsed)

    logger.info("Order %s → READY (%.1fs)", order_id, cook_time)
    await _notify_status(order_id, student_id, "READY")


async def _notify_status(order_id: str, student_id: str, status: str) -> None:
    """Push a status update to the Notification Service (fire-and-forget)."""
    url = f"{NOTIFICATION_SERVICE_URL.rstrip('/')}/notify"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
            await client.post(url, json={
                "order_id": order_id,
                "student_id": student_id,
                "status": status,
            })
    except Exception as exc:
        logger.warning("Failed to notify status %s for order %s: %s", status, order_id, exc)


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
