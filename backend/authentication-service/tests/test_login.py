"""
Unit tests for the authentication-service.

Redis calls are mocked throughout — no running Redis or Docker required.
"""
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LOGIN_URL = "/login"
VALID_PAYLOAD = {"student_id": "student001", "password": "password123"}
INVALID_PAYLOAD = {"student_id": "student001", "password": "wrongpassword"}


def _no_rate_limit(*_args, **_kwargs) -> bool:
    """Stub: never rate-limited."""
    return False


def _always_rate_limit(*_args, **_kwargs) -> bool:
    """Stub: always rate-limited."""
    return True


# ---------------------------------------------------------------------------
# POST /login — successful authentication
# ---------------------------------------------------------------------------


@patch("app.routes.login.is_rate_limited", side_effect=_no_rate_limit)
def test_login_success_returns_200(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    assert response.status_code == 200


@patch("app.routes.login.is_rate_limited", side_effect=_no_rate_limit)
def test_login_success_returns_access_token(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    body = response.json()
    assert "access_token" in body
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 0


# ---------------------------------------------------------------------------
# POST /login — invalid credentials
# ---------------------------------------------------------------------------


@patch("app.routes.login.is_rate_limited", side_effect=_no_rate_limit)
def test_login_invalid_password_returns_401(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=INVALID_PAYLOAD)
    assert response.status_code == 401


@patch("app.routes.login.is_rate_limited", side_effect=_no_rate_limit)
def test_login_unknown_student_returns_401(mock_rl, client: TestClient) -> None:
    response = client.post(
        LOGIN_URL, json={"student_id": "ghost999", "password": "anything"}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /login — rate limiting
# ---------------------------------------------------------------------------


@patch("app.routes.login.is_rate_limited", side_effect=_always_rate_limit)
def test_login_rate_limited_returns_429(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    assert response.status_code == 429


@patch("app.routes.login.is_rate_limited", side_effect=_always_rate_limit)
def test_login_rate_limited_error_message(mock_rl, client: TestClient) -> None:
    response = client.post(LOGIN_URL, json=VALID_PAYLOAD)
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# JWT payload correctness
# ---------------------------------------------------------------------------


@patch("app.routes.login.is_rate_limited", side_effect=_no_rate_limit)
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


@patch("app.routes.login.is_rate_limited", side_effect=_no_rate_limit)
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

    with patch("app.routes.health.get_redis_client", return_value=mock_redis):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["redis"] == "reachable"


def test_health_returns_503_when_redis_unreachable(client: TestClient) -> None:
    import redis as redis_lib

    mock_redis = MagicMock()
    mock_redis.ping.side_effect = redis_lib.RedisError("connection refused")

    with patch("app.routes.health.get_redis_client", return_value=mock_redis):
        response = client.get("/health")

    assert response.status_code == 503
