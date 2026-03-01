"""
Tests for error propagation and edge cases in the order flow.

Covers:
  - Stock service returns 409 Conflict (insufficient stock)
  - Stock service returns unexpected errors → 502 Bad Gateway
  - Failed idempotency key returns 409 with stored detail
  - Order record persisted in DB after success
  - Kitchen publish receives correct payload
  - Metrics counters for downstream failures and rejected orders
"""
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app

_JWT_SECRET = "test-secret-for-pytest-at-least-32-bytes!"


def _make_token(student_id: str = "stu-001") -> str:
    payload = {"student_id": student_id, "exp": int(time.time()) + 3600}
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _order_body(order_id: str | None = None, item_id: str = "burger", quantity: int = 1) -> dict:
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
# Stock service returns 409 Conflict (insufficient stock)
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_stock_409_returns_409_to_client(mock_deduct, mock_set, mock_get, client):
    """When stock-service returns 409 (insufficient stock), gateway forwards it."""
    mock_response = MagicMock()
    mock_response.status_code = 409
    mock_response.json.return_value = {"detail": "Insufficient stock for item"}
    mock_response.text = '{"detail": "Insufficient stock for item"}'
    mock_deduct.side_effect = httpx.HTTPStatusError(
        "409 Conflict", request=MagicMock(), response=mock_response
    )

    resp = client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert resp.status_code == 409


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_stock_409_updates_cache_to_zero(mock_deduct, mock_set, mock_get, client):
    """After a 409 from stock, the cache should be set to 0 for that item."""
    mock_response = MagicMock()
    mock_response.status_code = 409
    mock_response.json.return_value = {"detail": "Out of stock"}
    mock_response.text = '{"detail": "Out of stock"}'
    mock_deduct.side_effect = httpx.HTTPStatusError(
        "409", request=MagicMock(), response=mock_response
    )
    body = _order_body(item_id="sold-out-item")

    client.post(
        "/order",
        json=body,
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    mock_set.assert_called_once_with("sold-out-item", 0)


# ---------------------------------------------------------------------------
# Stock service unexpected error → 502 Bad Gateway
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_stock_unexpected_error_returns_502(mock_deduct, mock_set, mock_get, client):
    mock_deduct.side_effect = ConnectionError("Connection refused")

    resp = client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    assert resp.status_code == 502
    assert "unavailable" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Failed idempotency key → cached 409
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_failed_idempotency_returns_409(mock_deduct, mock_set, mock_get, client):
    """
    If a previous order with the same order_id FAILED (e.g. stock 409),
    re-sending the same order_id should return 409 without calling stock again.
    """
    oid = str(uuid.uuid4())
    mock_response = MagicMock()
    mock_response.status_code = 409
    mock_response.json.return_value = {"detail": "Insufficient stock"}
    mock_response.text = '{"detail": "Insufficient stock"}'
    mock_deduct.side_effect = httpx.HTTPStatusError(
        "409", request=MagicMock(), response=mock_response
    )

    # First call — fails at stock-service
    resp1 = client.post(
        "/order",
        json={"order_id": oid, "item_id": "out-item", "quantity": 1},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp1.status_code == 409

    # Second call — same order_id → idempotency returns cached 409
    mock_deduct.reset_mock()
    resp2 = client.post(
        "/order",
        json={"order_id": oid, "item_id": "out-item", "quantity": 1},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp2.status_code == 409
    # Stock-service should NOT have been called the second time
    mock_deduct.assert_not_called()


# ---------------------------------------------------------------------------
# Order record persisted in DB
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_successful_order_persisted_in_db(mock_publish, mock_deduct, mock_set, mock_get, client):
    """After a successful order, GatewayOrder and IdempotencyKey rows should exist."""
    from tests.conftest import _TestSessionLocal
    from app.models.order import GatewayOrder
    from app.models.idempotency import IdempotencyKey

    mock_deduct.return_value = {"remaining_stock": 5}
    oid = str(uuid.uuid4())

    resp = client.post(
        "/order",
        json={"order_id": oid, "item_id": "pizza", "quantity": 2},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )
    assert resp.status_code == 202

    db = _TestSessionLocal()
    from sqlalchemy import text
    # UUID stored as hex (no dashes) in SQLite, so normalize for comparison
    oid_hex = oid.replace("-", "")
    orders = db.execute(text("SELECT * FROM gateway_orders")).fetchall()
    assert len(orders) >= 1, f"Expected at least 1 order row, got {len(orders)}"
    our_order = [o for o in orders if o[1] == oid_hex or str(o[1]) == oid]
    assert len(our_order) == 1, f"Order {oid} not found. Rows: {orders}"
    order = our_order[0]
    assert order[2] == "stu-001"   # student_id
    assert order[3] == "pizza"     # item_id
    assert order[4] == 2           # quantity
    assert order[5] == "CONFIRMED" # status

    idem_rows = db.execute(text("SELECT * FROM idempotency_keys")).fetchall()
    our_idem = [i for i in idem_rows if i[1] == oid_hex or str(i[1]) == oid]
    assert len(our_idem) == 1, f"Idem key {oid} not found. Rows: {idem_rows}"
    # Columns: id(0), order_id(1), request_hash(2), response_payload(3), status(4)
    assert our_idem[0][4] == "CONFIRMED"
    db.close()


# ---------------------------------------------------------------------------
# Kitchen publish receives correct payload
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_kitchen_publish_contains_correct_data(mock_publish, mock_deduct, mock_set, mock_get, client):
    mock_deduct.return_value = {"remaining_stock": 3}
    oid = str(uuid.uuid4())

    client.post(
        "/order",
        json={"order_id": oid, "item_id": "pasta", "quantity": 1},
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    mock_publish.assert_called_once()
    event = mock_publish.call_args[0][0]
    assert event["order_id"] == oid
    assert event["item_id"] == "pasta"
    assert event["quantity"] == 1
    assert event["student_id"] == "stu-001"


# ---------------------------------------------------------------------------
# Metrics counters
# ---------------------------------------------------------------------------


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_downstream_failure_increments_counter(mock_deduct, mock_set, mock_get, client):
    from app.services.metrics import metrics

    mock_deduct.side_effect = httpx.TimeoutException("timed out")
    before = metrics.snapshot()["downstream_failures"]

    client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    after = metrics.snapshot()["downstream_failures"]
    assert after == before + 1


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
def test_rejected_order_increments_rejected_counter(mock_deduct, mock_set, mock_get, client):
    from app.services.metrics import metrics

    mock_deduct.side_effect = httpx.TimeoutException("timed out")
    before = metrics.snapshot()["rejected_orders"]

    client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    after = metrics.snapshot()["rejected_orders"]
    assert after == before + 1


@patch("app.routers.order.get_cached_stock", new_callable=AsyncMock, return_value=None)
@patch("app.routers.order.set_cached_stock", new_callable=AsyncMock)
@patch("app.routers.order.deduct_stock", new_callable=AsyncMock)
@patch("app.routers.order.publish_order_event")
def test_latency_recorded_on_success(mock_publish, mock_deduct, mock_set, mock_get, client):
    from app.services.metrics import metrics

    mock_deduct.return_value = {"remaining_stock": 1}
    before_avg = metrics.snapshot()["average_response_time_ms"]

    client.post(
        "/order",
        json=_order_body(),
        headers={"Authorization": f"Bearer {_make_token()}"},
    )

    after = metrics.snapshot()
    # After at least one order, avg should be > 0
    assert after["average_response_time_ms"] > 0
