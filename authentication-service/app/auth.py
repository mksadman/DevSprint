import time

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Simulated student store.
# In production replace this with a real database lookup.
# Passwords are stored as bcrypt hashes.
# ---------------------------------------------------------------------------
_STUDENT_DB: dict[str, str] = {
    "student001": _pwd_context.hash("password123"),
    "student002": _pwd_context.hash("securepass!"),
}


def _get_password_hash(password: str) -> str:
    return _pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def authenticate_student(student_id: str, password: str) -> bool:
    """Return True when the credentials are valid."""
    hashed = _STUDENT_DB.get(student_id)
    if hashed is None:
        return False
    return _verify_password(password, hashed)


def create_access_token(student_id: str) -> str:
    """
    Create a signed JWT containing:
      - student_id
      - iat  (issued-at, Unix timestamp)
      - exp  (expiry, Unix timestamp)
    """
    now = int(time.time())
    payload = {
        "student_id": student_id,
        "iat": now,
        "exp": now + settings.JWT_EXPIRY_MINUTES * 60,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
