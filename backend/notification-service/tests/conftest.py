"""
Pytest configuration for notification-service tests.

Sets environment variables before any app module is imported.
Uses an in-memory SQLite DB for isolation.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-at-least-32-bytes!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# In-memory SQLite shared across a single test
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
    import app.models.connection  # noqa: F401
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture(autouse=True)
def _reset_notifier():
    """Reset in-memory notifier state between tests."""
    from app.services import notifier
    notifier._connections.clear()
    notifier._total_messages_sent = 0
    notifier._failed_deliveries = 0
    yield
