"""
Tests that verify the Redis cache short-circuit logic:
  - stock == 0 in cache  →  HTTP 409, stock-service NOT called
  - stock > 0 in cache   →  stock-service IS called
  - cache miss (None)    →  stock-service IS called
  - short-circuit counter increments correctly
"""
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app

_JWT_SECRET = "test-secret-for-pytest-at-least-32-bytes!"


def _make_token(student_id: str = "stu-001") -> str:
    payload = {"student_id": student_id, "exp": int(time.time()) + 3600}
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _order_body(item_id: str = "burger") -> dict:
    return {"order_id": str(uuid.uuid4()), "item_id": item_id, "quantity": 1}


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# cache stock == 0  →  short-circuit
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=0)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_cache_zero_returns_409_without_hitting_stock_service(
    mock_deduct, mock_get, client
):
    resp = client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert resp.status_code == 409
    mock_deduct.assert_not_called()


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=0)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_cache_short_circuit_increments_counter(mock_deduct, mock_get, client):
    from app.services.metrics import metrics

    before = metrics.snapshot()["cache_short_circuits"]
    client.post(
        "/order",
        json=_order_body("pasta"),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert metrics.snapshot()["cache_short_circuits"] == before + 1


# ---------------------------------------------------------------------------
# cache stock > 0  →  proceed to stock-service
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=5)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_cache_positive_stock_calls_stock_service(
    mock_publish, mock_deduct, mock_set, mock_get, client
):
    mock_deduct.return_value = {"remaining_stock": 4}

    resp = client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert resp.status_code == 202
    mock_deduct.assert_called_once()


# ---------------------------------------------------------------------------
# cache miss (None)  →  proceed to stock-service
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_cache_miss_calls_stock_service(
    mock_publish, mock_deduct, mock_set, mock_get, client
):
    mock_deduct.return_value = {"remaining_stock": 10}

    resp = client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert resp.status_code == 202
    mock_deduct.assert_called_once()


# ---------------------------------------------------------------------------
# Cache write after stock-service success
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_cache_updated_after_successful_deduction(
    mock_publish, mock_deduct, mock_set, mock_get, client
):
    mock_deduct.return_value = {"remaining_stock": 7}
    body = _order_body("soda")

    client.post(
        "/order",
        json=body,
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    mock_set.assert_called_once_with(body["item_id"], 7)
