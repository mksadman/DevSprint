import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import Base, engine
from app.routers import order, health, metrics
from app.services.queue import close_rabbitmq
from app.services.order import close_http_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Ensure gateway_orders & idempotency_keys tables exist on startup."""
    if engine is not None:
        import app.models.order  # noqa: F401
        import app.models.idempotency  # noqa: F401
        Base.metadata.create_all(bind=engine)
    yield
    await close_rabbitmq()
    await close_http_client()


app = FastAPI(title="Order Gateway", version="1.0.0", lifespan=lifespan)

app.include_router(order.router)
app.include_router(health.router)
app.include_router(metrics.router)
