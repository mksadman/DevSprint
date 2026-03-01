import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.connection import Notification
from app.schemas.notification import HealthResponse, MetricsResponse, NotificationEvent
from app.services.notifier import (
    broadcast,
    get_active_connection_count,
    get_failed_deliveries,
    get_total_messages_sent,
    get_unique_students,
    send_to_student,
)
from app.services.consumer import check_rabbitmq_health, get_notifications_persisted

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ops"])


@router.get("/health", response_model=HealthResponse)
async def health(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Liveness / readiness probe.

    Returns 200 if service and dependencies are reachable,
    503 if any critical dependency is down.
    """
    rabbit_ok = await check_rabbitmq_health()
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    status = "ok" if (rabbit_ok and db_ok) else "degraded"
    resp = HealthResponse(
        status=status,
        rabbitmq="connected" if rabbit_ok else "unavailable",
        database="connected" if db_ok else "unavailable",
    )
    if status == "degraded":
        raise HTTPException(status_code=503, detail=resp.model_dump())
    return resp


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    """Expose WebSocket connection and message counters."""
    return MetricsResponse(
        total_messages_sent=get_total_messages_sent(),
        active_connections=get_active_connection_count(),
        unique_students=get_unique_students(),
        notifications_persisted=get_notifications_persisted(),
        failed_deliveries=get_failed_deliveries(),
    )


@router.post("/notify", status_code=200)
async def notify(event: NotificationEvent, db: Session = Depends(get_db)):
    """
    Receive order status updates (from kitchen-service or manual trigger)
    and push to the matching student's WebSocket connections.

    Also persists the notification to the database for audit history.
    """
    # Persist
    try:
        notif = Notification(
            order_id=event.order_id,
            student_id=event.student_id,
            status_sent=event.status,
        )
        db.add(notif)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to persist notification: %s", exc)

    # Push to student
    message = json.dumps({
        "event": "order_status",
        "payload": {
            "order_id": str(event.order_id),
            "student_id": event.student_id,
            "status": event.status,
        },
    })
    delivered = await send_to_student(event.student_id, message)
    return {
        "status": "sent",
        "delivered_to": delivered,
        "active_connections": get_active_connection_count(),
    }
