"""
Tests for the /health and /metrics observability endpoints (FR-20, FR-21, FR-22).

No live Redis or stock-service required — dependencies are mocked.
"""
import time
import uuid
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@patch("app.routers.health.stock_health_ping", new_callable=AsyncMock, return_value=True)
@patch("app.routers.health.redis_ping", new_callable=AsyncMock, return_value=True)
def test_health_returns_200_when_all_deps_ok(mock_redis, mock_stock, client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["dependencies"]["redis"] == "ok"
    assert body["dependencies"]["stock-service"] == "ok"


@patch("app.routers.health.stock_health_ping", new_callable=AsyncMock, return_value=True)
@patch("app.routers.health.redis_ping", new_callable=AsyncMock, return_value=False)
def test_health_degraded_when_redis_down(mock_redis, mock_stock, client):
    resp = client.get("/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["redis"] == "unreachable"


@patch("app.routers.health.stock_health_ping", new_callable=AsyncMock, return_value=False)
@patch("app.routers.health.redis_ping", new_callable=AsyncMock, return_value=True)
def test_health_degraded_when_stock_down(mock_redis, mock_stock, client):
    resp = client.get("/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["stock-service"] == "unreachable"


@patch("app.routers.health.stock_health_ping", new_callable=AsyncMock, return_value=False)
@patch("app.routers.health.redis_ping", new_callable=AsyncMock, return_value=False)
def test_health_degraded_when_all_deps_down(mock_redis, mock_stock, client):
    resp = client.get("/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["redis"] == "unreachable"
    assert body["dependencies"]["stock-service"] == "unreachable"


# ---------------------------------------------------------------------------
# GET /metrics
# ---------------------------------------------------------------------------


def test_metrics_returns_200(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_metrics_contains_required_fields(client):
    """FR-22: Metrics shall include total orders, failure count, avg latency."""
    resp = client.get("/metrics")
    body = resp.json()
    assert "total_orders" in body
    assert "successful_orders" in body
    assert "rejected_orders" in body
    assert "auth_failures" in body
    assert "cache_short_circuits" in body
    assert "downstream_failures" in body
    assert "average_response_time_ms" in body


def test_metrics_values_are_non_negative(client):
    resp = client.get("/metrics")
    body = resp.json()
    for key, value in body.items():
        assert value >= 0, f"{key} should be non-negative, got {value}"


def test_metrics_increment_after_failed_auth(client):
    """Auth failures should be tracked in metrics."""
    from app.services.metrics import metrics

    before = metrics.snapshot()["auth_failures"]
    # Send a request without a JWT
    client.post("/order", json={"order_id": str(uuid.uuid4()), "item_id": "x", "quantity": 1})
    after = metrics.snapshot()["auth_failures"]
    assert after == before + 1
