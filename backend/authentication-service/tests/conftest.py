"""
Pytest configuration for the authentication-service.

Environment variables are injected here *before* any app module is imported
so that pydantic-settings can resolve them without a .env file.
Uses in-memory SQLite for the database layer (no live PostgreSQL needed).
"""
import os

# Must be set before any app import — pydantic-settings reads env at class load
os.environ.setdefault("JWT_SECRET", "pytest-test-secret-key-not-for-production")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXP_MINUTES", "60")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.user import Base, User
from app.services.auth import hash_password

# ---------------------------------------------------------------------------
# In-memory SQLite engine (shared across the whole test session)
# ---------------------------------------------------------------------------
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_tables():
    """Create tables + seed demo students before every test, drop after."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = _override_get_db

    # Seed the two default students expected by existing tests
    db = TestingSessionLocal()
    if db.query(User).count() == 0:
        db.add(User(student_id="student001", password_hash=hash_password("password123")))
        db.add(User(student_id="student002", password_hash=hash_password("securepass!")))
        db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture()
def client() -> TestClient:
    """TestClient with the test-DB override already applied."""
    with TestClient(app) as c:
        yield c
