import os
from typing import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL: str = os.getenv("DATABASE_URL", "")

_pool_kwargs: dict = {}
if DATABASE_URL and not DATABASE_URL.startswith("sqlite"):
    _pool_kwargs = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

engine = create_engine(DATABASE_URL, **_pool_kwargs) if DATABASE_URL else None
SessionLocal = (
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
    if engine
    else None
)


def get_db():
    """Request-scoped DB session (for simple endpoints like list_orders)."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory() -> Callable[[], Session]:
    """Return a factory for creating short-lived DB sessions.

    Use this dependency when the handler needs to open/close sessions at
    different phases (e.g. release the connection during an HTTP call).
    """
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    return SessionLocal
