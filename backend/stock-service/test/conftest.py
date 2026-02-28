"""
Shared test fixtures for the Stock Service test suite.

Provides a single in-memory SQLite engine, session factory, and TestClient.
The autouse fixture ensures every test gets a fresh database and reset metrics.
"""
import os
import sys

# Set env BEFORE any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models import Base, get_db
from api import admin

# ---------------------------------------------------------------------------
# Single shared engine — all tests use this one DB
# ---------------------------------------------------------------------------
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop them after. Reset metrics."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Set the override so all API endpoints use our test DB
    app.dependency_overrides[get_db] = override_get_db

    # Reset in-memory metrics
    admin.metrics["total_requests"] = 0
    admin.metrics["total_deductions"] = 0
    admin.metrics["failed_deductions"] = 0
    admin.metrics["total_latency_ms"] = 0.0
    admin.metrics["request_count_per_route"] = {}

    yield TestingSessionLocal

    # Teardown: drop all tables for isolation
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    """FastAPI TestClient using the shared test DB."""
    return TestClient(app)


@pytest.fixture()
def db_session():
    """Raw DB session for seed-data insertion."""
    db = TestingSessionLocal()
    yield db
    db.close()
