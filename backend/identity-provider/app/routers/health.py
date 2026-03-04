import asyncio
import os

from fastapi import APIRouter, HTTPException

from app.schemas.auth import HealthResponse
from app.services.auth import check_redis_health

router = APIRouter(tags=["Ops"])


@router.post("/chaos/kill", summary="Chaos: kill this service process")
async def chaos_kill() -> dict:
    """Terminate the process after returning a response. Used by the Admin chaos panel."""
    async def _exit():
        await asyncio.sleep(0.5)
        os._exit(1)
    asyncio.create_task(_exit())
    return {"status": "dying", "service": "identity-provider"}


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Liveness / readiness probe used by Docker, Admin UI, and Judges.

    Returns 200 if service is running.
    """
    redis_ok = check_redis_health()
    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        redis="reachable" if redis_ok else "unreachable",
    )
