import json

from fastapi import APIRouter

from app.schemas.notification import HealthResponse, MetricsResponse, NotificationEvent
from app.services.notifier import (
    broadcast,
    get_active_connection_count,
    get_total_messages_sent,
)

router = APIRouter(tags=["Ops"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness / readiness probe."""
    return HealthResponse(status="ok", websocket="ready")


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    """Expose WebSocket connection and message counters."""
    return MetricsResponse(
        total_messages_sent=get_total_messages_sent(),
        active_connections=get_active_connection_count(),
    )


@router.post("/notify")
async def notify(event: NotificationEvent) -> dict:
    """
    Receive an order status update (from kitchen-service or order-gateway)
    and broadcast it to all connected WebSocket clients in real-time.
    """
    message = json.dumps({
        "event": "order_status",
        "payload": {
            "order_id": str(event.order_id),
            "student_id": event.student_id,
            "status": event.status,
        },
    })
    await broadcast(message)
    return {"status": "sent", "connections": get_active_connection_count()}
