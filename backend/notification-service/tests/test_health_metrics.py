"""Tests for /health and /metrics endpoints."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@patch("app.routers.health.check_rabbitmq_health", new_callable=AsyncMock, return_value=True)
def test_health_200_when_all_ok(mock_rabbit, client):
    """Health returns 200 when RabbitMQ and DB are reachable."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["rabbitmq"] == "connected"
    assert data["database"] == "connected"


@patch("app.routers.health.check_rabbitmq_health", new_callable=AsyncMock, return_value=False)
def test_health_200_when_rabbit_down(mock_rabbit, client):
    """Health returns 200 (degraded) when RabbitMQ is unreachable."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["rabbitmq"] == "unavailable"


@patch("app.routers.health.check_rabbitmq_health", new_callable=AsyncMock, return_value=True)
def test_health_response_contains_required_fields(mock_rabbit, client):
    resp = client.get("/health")
    data = resp.json()
    assert "status" in data
    assert "rabbitmq" in data
    assert "database" in data


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------

def test_metrics_returns_200(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_metrics_initial_values(client):
    resp = client.get("/metrics")
    data = resp.json()
    assert data["total_messages_sent"] == 0
    assert data["active_connections"] == 0
    assert data["unique_students"] == 0
    assert data["failed_deliveries"] == 0


def test_metrics_contains_all_required_fields(client):
    resp = client.get("/metrics")
    data = resp.json()
    required = [
        "total_messages_sent",
        "active_connections",
        "unique_students",
        "notifications_persisted",
        "failed_deliveries",
    ]
    for field in required:
        assert field in data, f"Missing field: {field}"


def test_metrics_values_non_negative(client):
    resp = client.get("/metrics")
    data = resp.json()
    for key, val in data.items():
        assert val >= 0, f"{key} should be >= 0, got {val}"
