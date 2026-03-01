import time

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_redis_client
import redis as redis_lib

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_STUDENT_DB: dict[str, str] = {
    "student001": _pwd_context.hash("password123"),
    "student002": _pwd_context.hash("securepass!"),
}


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def authenticate_student(student_id: str, password: str) -> bool:
    """Return True when the supplied credentials match the store."""
    hashed = _STUDENT_DB.get(student_id)
    if hashed is None:
        return False
    return _verify_password(password, hashed)


def create_access_token(student_id: str) -> str:
    """Return a signed HS256 JWT containing student_id, iat, and exp claims."""
    now = int(time.time())
    payload = {
        "student_id": student_id,
        "iat": now,
        "exp": now + settings.JWT_EXP_MINUTES * 60,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


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
