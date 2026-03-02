import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.connection import Notification
from app.schemas.notification import (
    HealthResponse,
    MetricsResponse,
    NotificationEvent,
    NotificationRecord,
)
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


@router.post("/chaos/kill", summary="Chaos: kill this service process")
async def chaos_kill() -> dict:
    """Terminate the process after returning a response. Used by the Admin chaos panel."""
    async def _exit():
        await asyncio.sleep(0.5)
        os._exit(1)
    asyncio.create_task(_exit())
    return {"status": "dying", "service": "notification-service"}


@router.get("/health", response_model=HealthResponse)
async def health(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Liveness / readiness probe.

    Returns 200 if service is running.
    Degraded status is reflected in the response body.
    """
    rabbit_ok = await check_rabbitmq_health()
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    status = "ok" if (rabbit_ok and db_ok) else "degraded"
    return HealthResponse(
        status=status,
        rabbitmq="connected" if rabbit_ok else "unavailable",
        database="connected" if db_ok else "unavailable",
    )


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


@router.get("/notifications", response_model=List[NotificationRecord])
async def get_notifications(
    student_id: str = Query(..., min_length=1, description="Student ID to query"),
    since: Optional[datetime] = Query(
        None,
        description="Return only notifications after this ISO-8601 timestamp",
    ),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[NotificationRecord]:
    """
    Retrieve persisted notifications for a student.

    Clients that reconnect after a WebSocket drop can call this endpoint
    to recover any notifications they missed.
    """
    query = db.query(Notification).filter(Notification.student_id == student_id)
    if since is not None:
        query = query.filter(Notification.sent_at > since)
    rows = query.order_by(Notification.sent_at.desc()).limit(limit).all()
    return rows
