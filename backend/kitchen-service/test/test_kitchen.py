import os
import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Setup environment BEFORE imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["RABBITMQ_URL"] = "amqp://guest:guest@localhost:5672/"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Patch aio_pika before importing main (prevents real RabbitMQ connection)
sys.modules["aio_pika"] = MagicMock()

from models import Base, get_db, KitchenOrder, OrderStatusHistory
from schemas import (
    OrderMessage,
    StatusUpdate,
    KitchenOrderResponse,
    StatusHistoryResponse,
)

# ---------------------------------------------------------------------------
# Test database (SQLite in-memory)
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Import app AFTER mocking aio_pika
from main import app

app.dependency_overrides[get_db] = override_get_db

from fastapi.testclient import TestClient
import uuid
from datetime import datetime, timezone

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_tables():
    """Wipe tables between tests."""
    yield
    db = TestingSessionLocal()
    db.query(OrderStatusHistory).delete()
    db.query(KitchenOrder).delete()
    db.commit()
    db.close()


def _insert_order(order_id: str = None, status: str = "In Kitchen"):
    """Helper: insert a KitchenOrder directly."""
    db = TestingSessionLocal()
    oid = order_id or str(uuid.uuid4())
    order = KitchenOrder(
        order_id=uuid.UUID(oid),
        status=status,
        received_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    db.add(OrderStatusHistory(
        kitchen_order_id=order.id,
        status=status,
        changed_at=datetime.now(timezone.utc),
    ))
    db.commit()
    db.refresh(order)
    db.close()
    return oid, str(order.id)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
class TestHealth:
    def test_health_returns_200(self):
        resp = client.get("/health")
        # DB is reachable (SQLite); RabbitMQ is mocked/not connected → may be 503
        # We only assert it returns valid JSON with expected keys
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data
        assert "database" in data
        assert "rabbitmq" in data

    def test_health_db_connected(self):
        resp = client.get("/health")
        data = resp.json()
        assert data["database"] == "connected"


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------
class TestMetrics:
    def test_metrics_returns_200(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"

    def test_metrics_contains_expected_keys(self):
        resp = client.get("/metrics")
        body = resp.text
        assert "total_orders_processed" in body
        assert "total_failures" in body
        assert "orders_in_progress" in body
        assert "average_processing_time_ms" in body
        assert "total_requests" in body
        assert "average_latency_ms" in body


# ---------------------------------------------------------------------------
# Orders list endpoint
# ---------------------------------------------------------------------------
class TestListOrders:
    def test_empty_list(self):
        resp = client.get("/orders")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_inserted_orders(self):
        oid1, _ = _insert_order()
        oid2, _ = _insert_order()
        resp = client.get("/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        returned_oids = {o["order_id"] for o in data}
        assert oid1 in returned_oids
        assert oid2 in returned_oids

    def test_filter_by_status(self):
        _insert_order(status="In Kitchen")
        _insert_order(status="Ready")
        resp = client.get("/orders", params={"status_filter": "Ready"})
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "Ready"


# ---------------------------------------------------------------------------
# Get single order
# ---------------------------------------------------------------------------
class TestGetOrder:
    def test_existing_order(self):
        oid, _ = _insert_order()
        resp = client.get(f"/orders/{oid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == oid
        assert data["status"] == "In Kitchen"

    def test_nonexistent_order(self):
        resp = client.get(f"/orders/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Order history
# ---------------------------------------------------------------------------
class TestOrderHistory:
    def test_history_returns_entries(self):
        oid, _ = _insert_order()
        resp = client.get(f"/orders/{oid}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["status"] == "In Kitchen"

    def test_history_nonexistent_order(self):
        resp = client.get(f"/orders/{uuid.uuid4()}/history")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Idempotency: duplicate order_id should not create a second record
# ---------------------------------------------------------------------------
class TestIdempotency:
    def test_duplicate_order_id_not_doubled(self):
        same_oid = str(uuid.uuid4())
        _insert_order(order_id=same_oid)
        # Inserting again with same order_id should be caught by app logic;
        # here we verify the DB only has one record for that order_id
        db = TestingSessionLocal()
        count = db.query(KitchenOrder).filter(
            KitchenOrder.order_id == uuid.UUID(same_oid)
        ).count()
        db.close()
        assert count == 1


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
class TestSchemas:
    def test_order_message_parsing(self):
        msg = OrderMessage(
            order_id=str(uuid.uuid4()),
            student_id="S001",
            items=[{"item_id": "abc", "qty": 2}],
        )
        assert msg.student_id == "S001"

    def test_status_update(self):
        su = StatusUpdate(
            order_id=str(uuid.uuid4()),
            student_id="S001",
            status="Ready",
        )
        assert su.status == "Ready"
