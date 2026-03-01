"""
Pytest configuration for the authentication-service.

Environment variables are injected here *before* any app module is imported
so that pydantic-settings can resolve them without a .env file.
"""
import os

# Must be set before any app import — pydantic-settings reads env at class load
os.environ.setdefault("JWT_SECRET", "pytest-test-secret-key-not-for-production")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXP_MINUTES", "60")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """TestClient with Redis rate-limiting bypassed (not rate-limited)."""
    with TestClient(app) as c:
        yield c
