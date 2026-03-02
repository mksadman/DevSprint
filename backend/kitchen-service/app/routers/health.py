import asyncio
import os

from fastapi import APIRouter

from app.schemas.status import HealthResponse, MetricsResponse
from app.services.processor import get_metrics_snapshot

router = APIRouter(tags=["Ops"])


@router.get("/health", response_model=HealthResponse, summary="Liveness / readiness probe")
async def health() -> HealthResponse:
    """Return 200 OK when the service is running and the queue is ready."""
    return HealthResponse(status="ok", queue="ready")


@router.get("/metrics", response_model=MetricsResponse, summary="Kitchen processing counters")
async def metrics() -> MetricsResponse:
    """Expose total orders received/processed and average cook time."""
    return MetricsResponse(**get_metrics_snapshot())


@router.post("/chaos/kill", summary="Chaos: kill this service process")
async def chaos_kill() -> dict:
    """Terminate the process after returning a response. Used by the Admin chaos panel."""
    async def _exit():
        await asyncio.sleep(0.5)
        os._exit(1)
    asyncio.create_task(_exit())
    return {"status": "dying", "service": "kitchen-service"}
