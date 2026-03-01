"""
Integration-style tests for the full order placement flow.

Redis and downstream HTTP services are mocked; no Docker required.
"""
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

# conftest.py sets env vars; this import triggers Settings() resolution
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JWT_SECRET = "test-secret-for-pytest-at-least-32-bytes!"


def _make_token(student_id: str = "stu-001") -> str:
    payload = {"student_id": student_id, "exp": int(time.time()) + 3600}
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _order_body(order_id: str | None = None, item_id: str = "burger", quantity: int = 2) -> dict:
    return {
        "order_id": order_id or str(uuid.uuid4()),
        "item_id": item_id,
        "quantity": quantity,
    }


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_successful_order_returns_202(mock_publish, mock_deduct, mock_set, mock_get, client):
    mock_deduct.return_value = {"remaining_stock": 5}
    body = _order_body()

    resp = client.post(
        "/order",
        json=body,
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert resp.status_code == 202
    data = resp.json()
    assert data["order_id"] == body["order_id"]
    assert data["status"] == "CONFIRMED"
    mock_deduct.assert_called_once_with(
        order_id=body["order_id"],
        item_id=body["item_id"],
        quantity=body["quantity"],
    )
    mock_publish.assert_called_once()


def test_missing_jwt_returns_401(client):
    resp = client.post("/order", json=_order_body())
    assert resp.status_code == 401


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_expired_jwt_returns_401(mock_deduct, mock_get, client):
    expired_payload = {"student_id": "stu-001", "exp": int(time.time()) - 100}
    expired_token = jwt.encode(expired_payload, _JWT_SECRET, algorithm="HS256")

    resp = client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert resp.status_code == 401
    mock_deduct.assert_not_called()


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_duplicate_order_id_not_double_decremented(
    mock_publish, mock_deduct, mock_set, mock_get, client
):
    """
    The gateway passes order_id to stock-service on every call.
    Stock-service is the idempotency source-of-truth; it returns 409 on duplicates.
    The gateway must propagate that 409 without any extra deduction.
    """
    oid = str(uuid.uuid4())
    mock_deduct.return_value = {"remaining_stock": 8}

    # First call — succeeds
    resp1 = client.post(
        "/order",
        json={"order_id": oid, "item_id": "pizza", "quantity": 1},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp1.status_code == 202

    # Stock-service signals duplicate on second call
    err_response = MagicMock(spec=httpx.Response)
    err_response.status_code = 409
    err_response.json.return_value = {"detail": "Duplicate order_id"}
    err_response.text = "Duplicate order_id"
    mock_deduct.side_effect = httpx.HTTPStatusError(
        "conflict", request=MagicMock(), response=err_response
    )

    resp2 = client.post(
        "/order",
        json={"order_id": oid, "item_id": "pizza", "quantity": 1},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp2.status_code == 409
    # deduct_stock called exactly once per HTTP request — never skipped or doubled
    assert mock_deduct.call_count == 2


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_stock_service_timeout_returns_504(mock_deduct, mock_set, mock_get, client):
    mock_deduct.side_effect = httpx.TimeoutException("timed out")

    resp = client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert resp.status_code == 504


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_redis_unavailable_falls_back_to_stock_service(
    mock_publish, mock_deduct, mock_set, mock_get, client
):
    """
    When Redis returns None (simulating an unreachable cache), the request
    must still proceed to stock-service and succeed.
    """
    mock_get.return_value = None  # cache miss / Redis down
    mock_deduct.return_value = {"remaining_stock": 3}

    resp = client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert resp.status_code == 202
    mock_deduct.assert_called_once()


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_successful_order_increments_metrics(
    mock_publish, mock_deduct, mock_set, mock_get, client
):
    from app.services.metrics import metrics

    mock_deduct.return_value = {"remaining_stock": 2}
    before = metrics.snapshot()

    client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    after = metrics.snapshot()
    assert after["total_orders"] == before["total_orders"] + 1
    assert after["successful_orders"] == before["successful_orders"] + 1
