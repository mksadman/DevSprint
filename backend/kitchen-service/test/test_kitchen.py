"""Kitchen Service tests — matches the new app/ package structure."""
import os
import sys

# Setup environment BEFORE imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["RABBITMQ_URL"] = "amqp://guest:guest@localhost:5672/"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.services import processor
from app.schemas.event import KitchenOrderEvent
from app.schemas.status import KitchenStatusUpdate, HealthResponse, MetricsResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_state():
    """Reset the in-memory queue and counters between tests."""
    processor._orders.clear()
    processor._seen_order_ids.clear()
    processor._store["total_orders_received"] = 0
    processor._store["total_orders_processed"] = 0
    processor._store["processing_times_ms"].clear()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def _post_order(client, order_id=None, item_id="item1", quantity=2, student_id="S001"):
    """Helper: enqueue an order via the API."""
    oid = order_id or str(uuid.uuid4())
    resp = client.post("/orders", json={
        "order_id": oid,
        "item_id": item_id,
        "quantity": quantity,
        "student_id": student_id,
    })
    return oid, resp


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["queue"] == "ready"

    def test_health_response_model(self, client):
        resp = client.get("/health")
        data = resp.json()
        model = HealthResponse(**data)
        assert model.status == "ok"


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------
class TestMetrics:
    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_initial_values(self, client):
        resp = client.get("/metrics")
        data = resp.json()
        assert data["total_orders_received"] == 0
        assert data["total_orders_processed"] == 0
        assert data["average_processing_time_ms"] == 0.0

    def test_metrics_after_enqueue(self, client):
        _post_order(client)
        resp = client.get("/metrics")
        data = resp.json()
        assert data["total_orders_received"] == 1


# ---------------------------------------------------------------------------
# POST /orders — enqueue
# ---------------------------------------------------------------------------
class TestEnqueueOrder:
    def test_enqueue_returns_202(self, client):
        oid, resp = _post_order(client)
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        assert data["order_id"] == oid

    def test_enqueue_multiple(self, client):
        _post_order(client)
        _post_order(client)
        resp = client.get("/metrics")
        assert resp.json()["total_orders_received"] == 2

    def test_enqueue_validation_error(self, client):
        resp = client.post("/orders", json={"bad": "data"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /orders/{order_id}/status
# ---------------------------------------------------------------------------
class TestGetOrderStatus:
    def test_not_found(self, client):
        resp = client.get(f"/orders/{uuid.uuid4()}/status")
        assert resp.status_code == 404

    def test_status_after_enqueue(self, client):
        """After enqueue the order should be in a valid processing state."""
        oid, _ = _post_order(client)
        resp = client.get(f"/orders/{oid}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == oid
        assert data["status"] in ("QUEUED", "IN_KITCHEN", "READY")


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
class TestSchemas:
    def test_kitchen_order_event(self):
        event = KitchenOrderEvent(
            order_id=str(uuid.uuid4()),
            item_id="item1",
            quantity=3,
            student_id="S001",
        )
        assert event.student_id == "S001"
        assert event.quantity == 3

    def test_kitchen_status_update(self):
        su = KitchenStatusUpdate(
            order_id=str(uuid.uuid4()),
            status="IN_KITCHEN",
        )
        assert su.status == "IN_KITCHEN"

    def test_metrics_response(self):
        mr = MetricsResponse(
            total_orders_received=10,
            total_orders_processed=5,
            average_processing_time_ms=123.456,
        )
        assert mr.total_orders_received == 10
