from fastapi import FastAPI

from app.routers import auth, health, metrics

app = FastAPI(title="Authentication Service", version="1.0.0")

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(metrics.router)
