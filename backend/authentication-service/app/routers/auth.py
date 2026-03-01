import time

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from app.services.auth import (
    authenticate_student,
    create_access_token,
    decode_access_token,
    is_rate_limited,
    record_login_attempt,
    register_student,
)
from app.services.metrics import record_attempt

router = APIRouter(tags=["Auth"])
_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse, status_code=200)
async def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
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

    user = authenticate_student(body.student_id, body.password, db)
    if user is None:
        elapsed = (time.perf_counter() - start) * 1000
        record_attempt(failed=True, elapsed_ms=elapsed)
        # Try to find user to record failed attempt in DB
        from app.models.user import User as UserModel
        db_user = db.query(UserModel).filter(UserModel.student_id == body.student_id).first()
        if db_user:
            record_login_attempt(db_user.id, success=False, response_time_ms=int(elapsed), db=db)
        raise HTTPException(status_code=401, detail="Invalid student_id or password.")

    token = create_access_token(body.student_id)
    elapsed = (time.perf_counter() - start) * 1000
    record_attempt(elapsed_ms=elapsed)
    record_login_attempt(user.id, success=True, response_time_ms=int(elapsed), db=db)
    return LoginResponse(access_token=token)


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """
    Register a new student account.

    - **201** student created
    - **409** student_id already exists
    - **422** validation error (password too short, etc.)
    """
    try:
        register_student(body.student_id, body.password, db)
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail=f"student_id '{body.student_id}' is already registered.",
        )
    return RegisterResponse(
        student_id=body.student_id,
        message="Student registered successfully.",
    )


@router.get("/me", response_model=UserResponse, status_code=200)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Return the authenticated user’s profile.

    Requires a valid ``Authorization: Bearer <JWT>`` header.

    - **200** user found
    - **401** missing / invalid / expired token
    - **404** token is valid but user no longer exists
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    student_id = payload.get("student_id")
    if not student_id:
        raise HTTPException(status_code=401, detail="Token missing student_id claim")

    user = db.query(User).filter(User.student_id == student_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)
