import logging
from typing import Any

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.services.metrics import metrics

logger = logging.getLogger(__name__)


def validate_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> dict[str, Any]:
    """
    Validate a Bearer JWT locally and return the decoded payload.

    Raises HTTP 401 on any of:
      - Missing / non-Bearer Authorization header
      - Invalid or tampered signature
      - Expired token
      - Token that does not contain ``student_id``
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        metrics.increment_auth_failures()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp"]},
        )
    except jwt.ExpiredSignatureError:
        metrics.increment_auth_failures()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        metrics.increment_auth_failures()
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if "student_id" not in payload:
        metrics.increment_auth_failures()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claim: student_id",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload
