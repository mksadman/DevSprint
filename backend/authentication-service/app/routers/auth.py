import time

from fastapi import APIRouter, HTTPException

from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth import authenticate_student, create_access_token, is_rate_limited
from app.services.metrics import record_attempt

router = APIRouter(tags=["Auth"])


@router.post("/login", response_model=LoginResponse, status_code=200)
async def login(body: LoginRequest) -> LoginResponse:
    """
    Authenticate a student and return a signed JWT.

    - **200** valid credentials → JWT
    - **401** invalid credentials
    - **429** rate-limit exceeded (> 3 attempts / 60 s per student_id)
    """
    start = time.perf_counter()

    if is_rate_limited(body.student_id):
        elapsed = (time.perf_counter() - start) * 1000
        record_attempt(rate_limited=True, elapsed_ms=elapsed)
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please wait and try again.",
        )

    if not authenticate_student(body.student_id, body.password):
        elapsed = (time.perf_counter() - start) * 1000
        record_attempt(failed=True, elapsed_ms=elapsed)
        raise HTTPException(status_code=401, detail="Invalid student_id or password.")

    token = create_access_token(body.student_id)
    elapsed = (time.perf_counter() - start) * 1000
    record_attempt(elapsed_ms=elapsed)
    return LoginResponse(access_token=token)
