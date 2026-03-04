import asyncio
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi import status

from app.services.cache import redis_ping
from app.services.order import stock_health_ping
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Ops"])


@router.post("/chaos/kill", summary="Chaos: kill this service process")
async def chaos_kill() -> dict:
    """Terminate the process after returning a response. Used by the Admin chaos panel."""
    async def _exit():
        await asyncio.sleep(0.5)
        os._exit(1)
    asyncio.create_task(_exit())
    return {"status": "dying", "service": "order-gateway"}


@router.get("/health", response_model=HealthResponse, summary="Dependency health check")
async def health() -> HealthResponse:
    redis_ok = await redis_ping()
    stock_ok = await stock_health_ping()

    overall = "ok" if (redis_ok and stock_ok) else "degraded"
    return HealthResponse(
        status=overall,
        redis="ok" if redis_ok else "unreachable",
        stock_service="ok" if stock_ok else "unreachable",
    )
