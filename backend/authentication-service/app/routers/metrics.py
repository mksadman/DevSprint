from fastapi import APIRouter

from app.schemas.auth import MetricsResponse
from app.services.metrics import get_snapshot

router = APIRouter(tags=["Ops"])


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    """
    Expose operational counters and latency statistics.

    - **total_login_attempts** — all POST /login calls, including blocked ones
    - **failed_attempts** — calls that returned 401
    - **rate_limit_blocks** — calls that returned 429
    - **average_response_time_ms** — mean end-to-end latency of POST /login
    """
    return MetricsResponse(**get_snapshot())
