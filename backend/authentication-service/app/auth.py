import time

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# In-memory student store (replace with a real database lookup in production).
# Passwords are stored as bcrypt hashes.
# ---------------------------------------------------------------------------
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
    """
    Return a signed HS256 JWT with the following claims:
      - student_id
      - iat  (issued-at, Unix epoch)
      - exp  (expiry, Unix epoch)
    """
    now = int(time.time())
    payload = {
        "student_id": student_id,
        "iat": now,
        "exp": now + settings.JWT_EXP_MINUTES * 60,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
