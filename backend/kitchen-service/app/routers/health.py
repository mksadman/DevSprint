import asyncio
import os

from fastapi import APIRouter, HTTPException

from app.schemas.status import HealthResponse, MetricsResponse
from app.services.processor import get_metrics_snapshot
from app.services.rabbitmq import check_rabbitmq_health

router = APIRouter(tags=["Ops"])


@router.get("/health", response_model=HealthResponse, summary="Liveness / readiness probe")
async def health() -> HealthResponse:
    """
    Liveness / readiness probe.

    Returns 200 if the service is running and RabbitMQ is reachable,
    503 if RabbitMQ is unavailable.
    """
    rabbit_ok = await check_rabbitmq_health()
    resp = HealthResponse(
        status="ok" if rabbit_ok else "degraded",
        queue="ready" if rabbit_ok else "unavailable",
        rabbitmq="connected" if rabbit_ok else "unavailable",
    )
    if not rabbit_ok:
        raise HTTPException(status_code=503, detail=resp.model_dump())
    return resp


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
