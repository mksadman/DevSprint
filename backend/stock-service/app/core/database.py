from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import DATABASE_URL

_pool_kwargs: dict = {}
if DATABASE_URL and not DATABASE_URL.startswith("sqlite"):
    _pool_kwargs = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

engine = create_engine(DATABASE_URL, **_pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health(db) -> bool:
    """Return True if the database is reachable."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
