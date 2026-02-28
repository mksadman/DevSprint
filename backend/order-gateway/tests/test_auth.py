"""
Unit tests for JWT validation logic in app/auth.py.

All tests are synchronous; no Docker or live services are required.
"""
import time

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# conftest.py has already set the env vars before this import
from app.services.auth import validate_token
from app.core.config import settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

JWT_SECRET = "test-secret-for-pytest-at-least-32-bytes!"
JWT_ALGORITHM = "HS256"


def _make_token(payload: dict, secret: str = JWT_SECRET, algorithm: str = JWT_ALGORITHM) -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


def _good_payload(student_id: str = "stu-001") -> dict:
    return {"student_id": student_id, "exp": int(time.time()) + 3600}


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="bearer", credentials=token)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_token_returns_payload():
    token = _make_token(_good_payload())
    payload = validate_token(_bearer(token))
    assert payload["student_id"] == "stu-001"


def test_missing_credentials_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        validate_token(None)
    assert exc_info.value.status_code == 401


def test_non_bearer_scheme_raises_401():
    token = _make_token(_good_payload())
    creds = HTTPAuthorizationCredentials(scheme="Basic", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        validate_token(creds)
    assert exc_info.value.status_code == 401


def test_invalid_signature_raises_401():
    token = _make_token(_good_payload(), secret="wrong-secret-key-that-is-long-enough-32b")
    with pytest.raises(HTTPException) as exc_info:
        validate_token(_bearer(token))
    assert exc_info.value.status_code == 401


def test_expired_token_raises_401():
    payload = {"student_id": "stu-001", "exp": int(time.time()) - 60}
    token = _make_token(payload)
    with pytest.raises(HTTPException) as exc_info:
        validate_token(_bearer(token))
    assert exc_info.value.status_code == 401


def test_missing_student_id_raises_401():
    payload = {"sub": "someone", "exp": int(time.time()) + 3600}
    token = _make_token(payload)
    with pytest.raises(HTTPException) as exc_info:
        validate_token(_bearer(token))
    assert exc_info.value.status_code == 401


def test_garbage_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        validate_token(_bearer("not.a.jwt"))
    assert exc_info.value.status_code == 401


def test_auth_failure_increments_metric():
    from app.services.metrics import metrics

    before = metrics.snapshot()["auth_failures"]
    with pytest.raises(HTTPException):
        validate_token(None)
    assert metrics.snapshot()["auth_failures"] == before + 1
