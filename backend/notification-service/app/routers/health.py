from fastapi import APIRouter

from app.schemas.notification import HealthResponse, MetricsResponse
from app.services.notifier import get_active_connection_count, get_total_messages_sent

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
