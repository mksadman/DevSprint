"""
Unit tests for the identity-provider.

Redis calls are mocked throughout — no running Redis or Docker required.
Database layer uses in-memory SQLite (configured in conftest.py).
"""
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LOGIN_URL = "/login"
REGISTER_URL = "/register"
ME_URL = "/me"
VALID_PAYLOAD = {"student_id": "student001", "password": "password123"}
INVALID_PAYLOAD = {"student_id": "student001", "password": "wrongpassword"}


def _no_rate_limit(*_args, **_kwargs) -> bool:
    """Stub: never rate-limited."""
    return False


def _always_rate_limit(*_args, **_kwargs) -> bool:
    """Stub: always rate-limited."""
    return True


def _get_valid_token(client: TestClient) -> str:
    """Helper: login and return a valid JWT."""
    with patch("app.routers.auth.is_rate_limited", side_effect=_no_rate_limit):
        resp = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# POST /login — successful authentication
# ---------------------------------------------------------------------------


@patch("app.routers.auth.is_rate_limited", side_effect=_no_rate_limit)
def test_login_success_returns_200(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    assert response.status_code == 200


@patch("app.routers.auth.is_rate_limited", side_effect=_no_rate_limit)
def test_login_success_returns_access_token(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    body = response.json()
    assert "access_token" in body
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 0


# ---------------------------------------------------------------------------
# POST /login — invalid credentials
# ---------------------------------------------------------------------------


@patch("app.routers.auth.is_rate_limited", side_effect=_no_rate_limit)
def test_login_invalid_password_returns_401(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=INVALID_PAYLOAD)
    assert response.status_code == 401


@patch("app.routers.auth.is_rate_limited", side_effect=_no_rate_limit)
def test_login_unknown_student_returns_401(mock_rl, client: TestClient) -> None:
    response = client.post(
        LOGIN_URL, json={"student_id": "ghost999", "password": "anything"}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /login — rate limiting
# ---------------------------------------------------------------------------


@patch("app.routers.auth.is_rate_limited", side_effect=_always_rate_limit)
def test_login_rate_limited_returns_429(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    assert response.status_code == 429


@patch("app.routers.auth.is_rate_limited", side_effect=_always_rate_limit)
def test_login_rate_limited_error_message(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# JWT payload correctness
# ---------------------------------------------------------------------------


@patch("app.routers.auth.is_rate_limited", side_effect=_no_rate_limit)
def test_jwt_payload_contains_required_claims(mock_rl, client: TestClient) -> None:
    before = int(time.time())
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    after = int(time.time())

    token = response.json()["access_token"]
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )

    # student_id must match
    assert payload["student_id"] == VALID_PAYLOAD["student_id"]

    # iat must be within the request window
    assert before <= payload["iat"] <= after

    # exp must be in the future and respect JWT_EXP_MINUTES
    expected_exp = payload["iat"] + settings.JWT_EXP_MINUTES * 60
    assert payload["exp"] == expected_exp
    assert payload["exp"] > after


@patch("app.routers.auth.is_rate_limited", side_effect=_no_rate_limit)
def test_jwt_signed_with_correct_algorithm(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    token = response.json()["access_token"]

    header = jwt.get_unverified_header(token)
    assert header["alg"] == settings.JWT_ALGORITHM


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_returns_200_when_redis_reachable(client: TestClient) -> None:
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with patch("app.services.auth.get_redis_client", return_value=mock_redis):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["redis"] == "reachable"


def test_health_returns_200_degraded_when_redis_unreachable(client: TestClient) -> None:
    import redis as redis_lib

    mock_redis = MagicMock()
    mock_redis.ping.side_effect = redis_lib.RedisError("connection refused")

    with patch("app.services.auth.get_redis_client", return_value=mock_redis):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["redis"] == "unreachable"


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------


def test_register_success_returns_201(client: TestClient) -> None:
    response = client.post(
        REGISTER_URL,
        json={"student_id": "newstudent99", "password": "strongpass"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["student_id"] == "newstudent99"
    assert "message" in body


def test_register_duplicate_returns_409(client: TestClient) -> None:
    # student001 is pre-seeded
    response = client.post(
        REGISTER_URL,
        json={"student_id": "student001", "password": "anotherpass1"},
    )
    assert response.status_code == 409


def test_register_short_password_returns_422(client: TestClient) -> None:
    response = client.post(
        REGISTER_URL,
        json={"student_id": "shortpw", "password": "ab"},
    )
    assert response.status_code == 422


@patch("app.routers.auth.is_rate_limited", side_effect=_no_rate_limit)
def test_register_then_login(mock_rl, client: TestClient) -> None:
    """Newly registered student can immediately log in."""
    client.post(
        REGISTER_URL,
        json={"student_id": "fresh001", "password": "mypassword"},
    )
    resp = client.post(
        LOGIN_URL,
        json={"student_id": "fresh001", "password": "mypassword"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


def test_me_returns_200_with_valid_token(client: TestClient) -> None:
    token = _get_valid_token(client)
    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == "student001"
    assert "created_at" in body


def test_me_returns_401_without_token(client: TestClient) -> None:
    response = client.get(ME_URL)
    assert response.status_code == 401


def test_me_returns_401_with_invalid_token(client: TestClient) -> None:
    response = client.get(
        ME_URL, headers={"Authorization": "Bearer garbage.token.here"}
    )
    assert response.status_code == 401


def test_me_returns_401_with_expired_token(client: TestClient) -> None:
    # Create a token that expired 1 hour ago
    import time as _time

    now = int(_time.time())
    payload = {"student_id": "student001", "iat": now - 7200, "exp": now - 3600}
    expired = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    response = client.get(ME_URL, headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Login attempts audit (DB persistence)
# ---------------------------------------------------------------------------


@patch("app.routers.auth.is_rate_limited", side_effect=_no_rate_limit)
def test_login_records_attempt_in_db(mock_rl, client: TestClient) -> None:
    """Successful login creates a LoginAttempt row with success=True."""
    from tests.conftest import TestingSessionLocal
    from app.models.user import LoginAttempt

    client.post(LOGIN_URL, json=VALID_PAYLOAD)

    db = TestingSessionLocal()
    attempts = db.query(LoginAttempt).all()
    db.close()
    assert len(attempts) >= 1
    assert any(a.success is True for a in attempts)
