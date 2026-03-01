import threading
from typing import List
from uuid import UUID

from app.schemas.event import KitchenOrderEvent
from app.models.job import KitchenOrder


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
