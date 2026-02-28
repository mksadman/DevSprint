from collections import deque
from threading import Lock

from fastapi import APIRouter

from app.models import MetricsResponse

router = APIRouter(tags=["Ops"])

# ---------------------------------------------------------------------------
# In-process metrics store.
# Thread-safe via a Lock; bounded deque avoids unbounded memory growth.
# ---------------------------------------------------------------------------
_lock = Lock()
_store: dict = {
    "total_login_attempts": 0,
    "failed_attempts": 0,
    "rate_limit_blocks": 0,
    "response_times_ms": deque(maxlen=10_000),
}


def record_attempt(
    *,
    failed: bool = False,
    rate_limited: bool = False,
    elapsed_ms: float | None = None,
) -> None:
    """Update counters after every login attempt (success, failure, or block)."""
    with _lock:
        _store["total_login_attempts"] += 1
        if failed:
            _store["failed_attempts"] += 1
        if rate_limited:
            _store["rate_limit_blocks"] += 1
        if elapsed_ms is not None:
            _store["response_times_ms"].append(elapsed_ms)


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    """
    Expose operational counters and latency statistics.

    - **total_login_attempts** — all POST /login calls, including blocked ones
    - **failed_attempts** — calls that returned 401
    - **rate_limit_blocks** — calls that returned 429
    - **average_response_time_ms** — mean end-to-end latency of POST /login
    """
    with _lock:
        times = list(_store["response_times_ms"])
        avg_ms = sum(times) / len(times) if times else 0.0
        return MetricsResponse(
            total_login_attempts=_store["total_login_attempts"],
            failed_attempts=_store["failed_attempts"],
            rate_limit_blocks=_store["rate_limit_blocks"],
            average_response_time_ms=round(avg_ms, 3),
        )
