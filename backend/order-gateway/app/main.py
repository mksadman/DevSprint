import logging

from fastapi import FastAPI

from app.routers import order, health, metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(title="Order Gateway", version="1.0.0")

app.include_router(order.router)
app.include_router(health.router)
app.include_router(metrics.router)
