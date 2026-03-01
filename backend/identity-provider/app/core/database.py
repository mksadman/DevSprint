import redis as redis_lib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# ---------------------------------------------------------------------------
# PostgreSQL (SQLAlchemy)
# ---------------------------------------------------------------------------
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a SQLAlchemy session, closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Redis (rate-limiting)
# ---------------------------------------------------------------------------
_redis_pool = redis_lib.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    max_connections=20,
    socket_connect_timeout=2,
)


def get_redis_client() -> redis_lib.Redis:
    """Return a Redis client backed by a shared connection pool."""
    return redis_lib.Redis(connection_pool=_redis_pool)
