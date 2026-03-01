"""
Pytest configuration for order-gateway tests.

Environment variables are set here — at collection time — before any app
module is imported, so pydantic-settings can resolve them without a real
.env file or live infrastructure.
"""
import os

# Required by app/config.py — must be set before the first import of any app module.
# Key is >= 32 bytes to satisfy HS256 minimum key-length recommendations.
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-at-least-32-bytes!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("STOCK_SERVICE_URL", "http://stock-service:8001")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
os.environ.setdefault("INTERNAL_API_KEY", "internal-service-key-2026")
os.environ.setdefault("GATEWAY_TIMEOUT_MS", "2000")
os.environ.setdefault("DATABASE_URL", "sqlite:///")  # in-memory

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# In-memory SQLite — shared across a single test so the same connection is reused.
_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


def _override_get_db():
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _reset_tables():
    """Create all tables before each test and drop them after."""
    # Import models so they are registered on Base.metadata
    import app.models.order  # noqa: F401
    import app.models.idempotency  # noqa: F401

    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)
