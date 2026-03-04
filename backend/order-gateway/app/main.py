import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.core.config import settings
from app.routers import order, health, metrics
from app.services.queue import close_rabbitmq, start_outbox_relay
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
        import app.models.outbox  # noqa: F401
        Base.metadata.create_all(bind=engine)
    start_outbox_relay()
    yield
    await close_rabbitmq()
    await close_http_client()


app = FastAPI(title="Order Gateway", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(order.router)
app.include_router(health.router)
app.include_router(metrics.router)
