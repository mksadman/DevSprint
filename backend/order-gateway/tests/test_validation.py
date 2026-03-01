"""
Tests for request body validation on POST /order.

Ensures malformed, incomplete, or out-of-range payloads are rejected with 422
before any business logic runs.
"""
import time
import uuid
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app

_JWT_SECRET = "test-secret-for-pytest-at-least-32-bytes!"


def _make_token(student_id: str = "stu-001") -> str:
    payload = {"student_id": student_id, "exp": int(time.time()) + 3600}
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


_AUTH_HEADER = {"Authorization": f"Bearer {jwt.encode({'student_id': 'stu-001', 'exp': int(time.time()) + 3600}, _JWT_SECRET, algorithm='HS256')}"}


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------


def test_missing_order_id_returns_422(client):
    resp = client.post(
        "/order",
        json={"item_id": "burger", "quantity": 1},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 422


def test_missing_item_id_returns_422(client):
    resp = client.post(
        "/order",
        json={"order_id": str(uuid.uuid4()), "quantity": 1},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 422


def test_missing_quantity_returns_422(client):
    resp = client.post(
        "/order",
        json={"order_id": str(uuid.uuid4()), "item_id": "burger"},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 422


def test_empty_body_returns_422(client):
    resp = client.post(
        "/order",
        json={},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Invalid field values
# ---------------------------------------------------------------------------


def test_quantity_zero_returns_422(client):
    resp = client.post(
        "/order",
        json={"order_id": str(uuid.uuid4()), "item_id": "burger", "quantity": 0},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 422


def test_negative_quantity_returns_422(client):
    resp = client.post(
        "/order",
        json={"order_id": str(uuid.uuid4()), "item_id": "burger", "quantity": -5},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 422


def test_empty_item_id_returns_422(client):
    resp = client.post(
        "/order",
        json={"order_id": str(uuid.uuid4()), "item_id": "", "quantity": 1},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 422


def test_invalid_order_id_format_returns_422(client):
    resp = client.post(
        "/order",
        json={"order_id": "not-a-uuid", "item_id": "burger", "quantity": 1},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 422


def test_quantity_string_returns_422(client):
    resp = client.post(
        "/order",
        json={"order_id": str(uuid.uuid4()), "item_id": "burger", "quantity": "two"},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 422
