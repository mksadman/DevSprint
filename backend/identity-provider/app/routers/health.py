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

    - **200** service is running AND Redis is reachable
    - **503** Redis (or another critical dependency) is unreachable
    """
    if not check_redis_health():
        raise HTTPException(
            status_code=503,
            detail="Redis unreachable",
        )

    return HealthResponse(status="ok", redis="reachable")
