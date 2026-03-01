from fastapi import APIRouter, HTTPException

from app.schemas.auth import HealthResponse
from app.services.auth import check_redis_health

router = APIRouter(tags=["Ops"])


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
