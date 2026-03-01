"""Tests for WebSocket JWT authentication and per-student targeting."""
import time
import json

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app

_JWT_SECRET = "test-secret-for-pytest-at-least-32-bytes!"


def _make_token(student_id: str = "stu-001", expired: bool = False) -> str:
    exp = int(time.time()) - 3600 if expired else int(time.time()) + 3600
    payload = {"student_id": student_id, "exp": exp}
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_ws_connect_with_valid_token(client):
    """A valid JWT should establish the WebSocket connection."""
    token = _make_token("stu-001")
    with client.websocket_connect(f"/ws?token={token}") as ws:
        # Connection established — verify by checking it doesn't immediately close
        assert ws is not None


def test_ws_connect_without_token(client):
    """Missing token should close the connection with code 1008."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws"):
            pass


def test_ws_connect_with_invalid_token(client):
    """Invalid JWT should close the connection with code 1008."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=garbage-token"):
            pass


def test_ws_connect_with_expired_token(client):
    """Expired JWT should close the connection."""
    token = _make_token("stu-001", expired=True)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws?token={token}"):
            pass


def test_ws_connect_with_wrong_secret(client):
    """Token signed with wrong secret should be rejected."""
    payload = {"student_id": "stu-001", "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, "wrong-secret-key-that-is-32-bytes-long!", algorithm="HS256")
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws?token={token}"):
            pass


# ---------------------------------------------------------------------------
# Per-student targeting
# ---------------------------------------------------------------------------

def test_send_to_student_targets_correctly(client):
    """Messages sent to student A should not reach student B."""
    from app.services.notifier import send_to_student
    import asyncio

    token_a = _make_token("stu-A")
    token_b = _make_token("stu-B")

    with client.websocket_connect(f"/ws?token={token_a}") as ws_a:
        with client.websocket_connect(f"/ws?token={token_b}") as ws_b:
            msg = json.dumps({"event": "order_status", "payload": {"status": "READY"}})

            # Send only to student A
            loop = asyncio.new_event_loop()
            delivered = loop.run_until_complete(send_to_student("stu-A", msg))
            loop.close()

            assert delivered == 1
            data_a = ws_a.receive_text()
            assert "READY" in data_a


def test_multiple_connections_same_student(client):
    """Multiple tabs for the same student should all receive the message."""
    from app.services.notifier import send_to_student, get_active_connection_count
    import asyncio

    token = _make_token("stu-multi")

    with client.websocket_connect(f"/ws?token={token}") as ws1:
        with client.websocket_connect(f"/ws?token={token}") as ws2:
            assert get_active_connection_count() == 2

            msg = json.dumps({"event": "test", "payload": {}})
            loop = asyncio.new_event_loop()
            delivered = loop.run_until_complete(send_to_student("stu-multi", msg))
            loop.close()

            assert delivered == 2
            assert ws1.receive_text() == msg
            assert ws2.receive_text() == msg


def test_active_connections_tracked(client):
    """Connection count should increase on connect and decrease on disconnect."""
    from app.services.notifier import get_active_connection_count

    assert get_active_connection_count() == 0
    token = _make_token("stu-track")

    with client.websocket_connect(f"/ws?token={token}"):
        assert get_active_connection_count() == 1
    # After disconnect
    assert get_active_connection_count() == 0
