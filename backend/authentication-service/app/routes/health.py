import redis as redis_lib
from fastapi import APIRouter, HTTPException

from app.models import HealthResponse
from app.rate_limit import get_redis_client

router = APIRouter(tags=["Ops"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Liveness / readiness probe used by Docker, Admin UI, and Judges.

    - **200** service is running AND Redis is reachable
    - **503** Redis (or another critical dependency) is unreachable
    """
    try:
        client = get_redis_client()
        client.ping()
    except redis_lib.RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Redis unreachable: {exc}",
        ) from exc

    return HealthResponse(status="ok", redis="reachable")
