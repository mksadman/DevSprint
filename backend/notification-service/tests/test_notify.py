"""Tests for the POST /notify endpoint — persistence and delivery."""
import json
import time
import uuid

import jwt
import pytest
from unittest.mock import patch, AsyncMock
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


def _notify_body(order_id: str | None = None, student_id: str = "stu-001", status: str = "READY"):
    return {
        "order_id": order_id or str(uuid.uuid4()),
        "student_id": student_id,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Basic /notify behaviour
# ---------------------------------------------------------------------------

def test_notify_returns_200(client):
    resp = client.post("/notify", json=_notify_body())
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"


def test_notify_returns_delivery_count(client):
    """With no WS connections, delivered_to should be 0."""
    resp = client.post("/notify", json=_notify_body())
    assert resp.json()["delivered_to"] == 0


def test_notify_delivers_to_connected_student(client):
    """POST /notify should push the message to the student's WebSocket."""
    token = _make_token("stu-ws")

    with client.websocket_connect(f"/ws?token={token}") as ws:
        oid = str(uuid.uuid4())
        resp = client.post("/notify", json=_notify_body(order_id=oid, student_id="stu-ws"))
        assert resp.status_code == 200
        assert resp.json()["delivered_to"] == 1

        # Verify WS received the message
        raw = ws.receive_text()
        data = json.loads(raw)
        assert data["event"] == "order_status"
        assert data["payload"]["order_id"] == oid
        assert data["payload"]["student_id"] == "stu-ws"
        assert data["payload"]["status"] == "READY"


def test_notify_does_not_deliver_to_wrong_student(client):
    """Student B should NOT receive student A's notification."""
    token_b = _make_token("stu-B")

    with client.websocket_connect(f"/ws?token={token_b}"):
        resp = client.post("/notify", json=_notify_body(student_id="stu-A"))
        assert resp.json()["delivered_to"] == 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_notify_persists_to_db(client):
    """POST /notify should create a Notification row in the database."""
    from tests.conftest import _TestSessionLocal
    from sqlalchemy import text

    oid = str(uuid.uuid4())
    client.post("/notify", json=_notify_body(order_id=oid, student_id="stu-db", status="IN_KITCHEN"))

    db = _TestSessionLocal()
    rows = db.execute(text("SELECT * FROM notifications")).fetchall()
    assert len(rows) >= 1
    # Find our notification — order_id may be stored as UUID hex (no dashes) or full string
    oid_hex = oid.replace("-", "")
    found = [r for r in rows if oid_hex in str(r[1]).replace("-", "")]
    assert len(found) == 1, f"Expected notification for {oid}, rows={rows}"
    db.close()


def test_notify_persists_correct_fields(client):
    """Verify persisted notification has correct student_id and status."""
    from tests.conftest import _TestSessionLocal
    from sqlalchemy import text

    oid = str(uuid.uuid4())
    client.post("/notify", json=_notify_body(order_id=oid, student_id="stu-persist", status="READY"))

    db = _TestSessionLocal()
    rows = db.execute(text("SELECT * FROM notifications")).fetchall()
    assert len(rows) >= 1
    # columns: id(0), order_id(1), student_id(2), status_sent(3), sent_at(4)
    row = rows[-1]
    assert row[2] == "stu-persist"
    assert row[3] == "READY"
    db.close()


# ---------------------------------------------------------------------------
# Metrics after notify
# ---------------------------------------------------------------------------

def test_notify_increments_messages_sent(client):
    """After delivering to a connected student, total_messages_sent should increase."""
    token = _make_token("stu-metric")

    with client.websocket_connect(f"/ws?token={token}"):
        client.post("/notify", json=_notify_body(student_id="stu-metric"))

    resp = client.get("/metrics")
    assert resp.json()["total_messages_sent"] >= 1


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_notify_missing_order_id_returns_422(client):
    resp = client.post("/notify", json={"student_id": "s1", "status": "READY"})
    assert resp.status_code == 422


def test_notify_missing_student_id_returns_422(client):
    resp = client.post("/notify", json={"order_id": str(uuid.uuid4()), "status": "READY"})
    assert resp.status_code == 422


def test_notify_missing_status_returns_422(client):
    resp = client.post("/notify", json={"order_id": str(uuid.uuid4()), "student_id": "s1"})
    assert resp.status_code == 422
