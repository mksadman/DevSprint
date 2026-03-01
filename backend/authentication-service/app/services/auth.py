import time

import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_redis_client
from app.models.user import LoginAttempt, User
import redis as redis_lib

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plaintext password."""
    return _pwd_context.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def authenticate_student(student_id: str, password: str, db: Session) -> User | None:
    """Return the User row if credentials match, else None."""
    user = db.query(User).filter(User.student_id == student_id).first()
    if user is None:
        return None
    if not _verify_password(password, user.password_hash):
        return None
    return user


def register_student(student_id: str, password: str, db: Session) -> User:
    """Create a new user. Raises ValueError if student_id already taken."""
    existing = db.query(User).filter(User.student_id == student_id).first()
    if existing is not None:
        raise ValueError(f"student_id '{student_id}' already registered")
    user = User(student_id=student_id, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def record_login_attempt(
    user_id: str, success: bool, response_time_ms: int, db: Session
) -> None:
    """Persist a login attempt to the login_attempts table."""
    attempt = LoginAttempt(
        user_id=user_id,
        success=success,
        response_time_ms=response_time_ms,
    )
    db.add(attempt)
    db.commit()


def create_access_token(student_id: str) -> str:
    """Return a signed HS256 JWT containing student_id, iat, and exp claims."""
    now = int(time.time())
    payload = {
        "student_id": student_id,
        "iat": now,
        "exp": now + settings.JWT_EXP_MINUTES * 60,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.* exceptions on failure."""
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp"]},
    )


def is_rate_limited(student_id: str) -> bool:
    """
    Increment the per-student login attempt counter.

    Returns True (block the request) when the student has exceeded
    RATE_LIMIT_MAX_ATTEMPTS within the RATE_LIMIT_WINDOW_SECONDS window.
    Fails open — if Redis is unreachable the request is allowed through.
    """
    try:
        client = get_redis_client()
        key = f"rl:login:{student_id}"

        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
        results = pipe.execute()

        attempt_count: int = results[0]
        return attempt_count > settings.RATE_LIMIT_MAX_ATTEMPTS
    except redis_lib.RedisError:
        return False


def check_redis_health() -> bool:
    """Return True if Redis is reachable, False otherwise."""
    try:
        client = get_redis_client()
        client.ping()
        return True
    except redis_lib.RedisError:
        return False
