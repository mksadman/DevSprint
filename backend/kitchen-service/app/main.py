import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import health, queue
from app.core.database import Base, engine
from app.services.rabbitmq import start_consumer, close_rabbitmq

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Start the RabbitMQ consumer on startup and close on shutdown."""
    # Create DB tables for KitchenOrder / OrderStatusHistory
    try:
        import app.models.job  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Kitchen tables created")
    except Exception as exc:
        logger.warning("Kitchen DB table creation failed: %s", exc)

    try:
        import asyncio
        await asyncio.wait_for(start_consumer(), timeout=2.0)
        logger.info("Kitchen RabbitMQ consumer started")
    except Exception as exc:
        logger.warning("RabbitMQ consumer startup skipped: %s", type(exc).__name__)
    yield
    try:
        await close_rabbitmq()
    except Exception:
        pass


app = FastAPI(title="Kitchen Service", version="1.0.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(queue.router)
