from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine
from app.models.user import Base, User
from app.routers import auth, health, metrics
from app.services.auth import hash_password


def _seed_default_students(engine) -> None:
    """Insert the two demo students if the users table is empty."""
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        if db.query(User).count() == 0:
            db.add(User(student_id="student001", password_hash=hash_password("password123")))
            db.add(User(student_id="student002", password_hash=hash_password("securepass!")))
            db.commit()


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup: create tables and seed demo data
    Base.metadata.create_all(bind=engine)
    _seed_default_students(engine)
    yield


app = FastAPI(title="Authentication Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(metrics.router)
