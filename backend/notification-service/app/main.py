import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.routers import health, websocket
from app.services.consumer import start_consumer, close_rabbitmq

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Create DB tables and start RabbitMQ consumer on startup."""
    # Ensure the notifications table exists
    try:
        import app.models.connection  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Notification tables created")
    except Exception as exc:
        logger.warning("DB table creation failed: %s", exc)

    # Start RabbitMQ consumer
    try:
        import asyncio
        await asyncio.wait_for(start_consumer(), timeout=5.0)
        logger.info("Notification RabbitMQ consumer started")
    except Exception as exc:
        logger.warning("RabbitMQ consumer startup skipped: %s", type(exc).__name__)

    yield

    try:
        await close_rabbitmq()
    except Exception:
        pass


app = FastAPI(title="Notification Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(websocket.router)
