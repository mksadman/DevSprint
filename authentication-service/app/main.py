import time
from collections import deque
from threading import Lock

import redis as redis_lib
from fastapi import FastAPI, HTTPException, Request

from app.auth import authenticate_student, create_access_token
from app.config import settings
from app.models import HealthResponse, LoginRequest, LoginResponse, MetricsResponse
from app.rate_limit import get_redis_client, is_rate_limited

app = FastAPI(title="Identity Provider", version="1.0.0")

# ---------------------------------------------------------------------------
# In-process metrics store (thread-safe with a Lock).
# Uses a bounded deque for response times to avoid unbounded memory growth.
# ---------------------------------------------------------------------------
_metrics_lock = Lock()
_metrics = {
    "total_login_attempts": 0,
    "failed_attempts": 0,
    "rate_limit_blocks": 0,
    "response_times_ms": deque(maxlen=10_000),  # keep last 10 000 samples
}


def _record_attempt(
    *,
    failed: bool = False,
    rate_limited: bool = False,
    elapsed_ms: float | None = None,
) -> None:
    with _metrics_lock:
        _metrics["total_login_attempts"] += 1
        if failed:
            _metrics["failed_attempts"] += 1
        if rate_limited:
            _metrics["rate_limit_blocks"] += 1
        if elapsed_ms is not None:
            _metrics["response_times_ms"].append(elapsed_ms)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/login", response_model=LoginResponse, status_code=200)
async def login(body: LoginRequest) -> LoginResponse:
    """
    Authenticate a student and return a signed JWT.

    - 200  valid credentials → JWT
    - 401  invalid credentials
    - 429  rate-limit exceeded (> 3 attempts / 60 s per student_id)
    """
    start = time.perf_counter()

    # ── Rate-limit check ──────────────────────────────────────────────────
    if is_rate_limited(body.student_id):
        elapsed = (time.perf_counter() - start) * 1000
        _record_attempt(rate_limited=True, elapsed_ms=elapsed)
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please wait and try again.",
        )

    # ── Credential check ──────────────────────────────────────────────────
    if not authenticate_student(body.student_id, body.password):
        elapsed = (time.perf_counter() - start) * 1000
        _record_attempt(failed=True, elapsed_ms=elapsed)
        raise HTTPException(status_code=401, detail="Invalid student_id or password.")

    # ── Success ───────────────────────────────────────────────────────────
    token = create_access_token(body.student_id)
    elapsed = (time.perf_counter() - start) * 1000
    _record_attempt(elapsed_ms=elapsed)
    return LoginResponse(access_token=token)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Liveness / readiness probe.

    - 200  service is running AND Redis is reachable
    - 503  Redis (or another critical dependency) is unreachable
    """
    try:
        client = get_redis_client()
        client.ping()
        redis_status = "reachable"
    except redis_lib.RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Redis unreachable: {exc}",
        ) from exc

    return HealthResponse(status="ok", redis=redis_status)


@app.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    """
    Expose operational counters and latency statistics.

    Fields
    ------
    total_login_attempts    all POST /login calls (including blocked ones)
    failed_attempts         calls that returned 401
    rate_limit_blocks       calls that returned 429
    average_response_time_ms  mean end-to-end latency of POST /login in ms
    """
    with _metrics_lock:
        times = list(_metrics["response_times_ms"])
        avg_ms = sum(times) / len(times) if times else 0.0
        return MetricsResponse(
            total_login_attempts=_metrics["total_login_attempts"],
            failed_attempts=_metrics["failed_attempts"],
            rate_limit_blocks=_metrics["rate_limit_blocks"],
            average_response_time_ms=round(avg_ms, 3),
        )
