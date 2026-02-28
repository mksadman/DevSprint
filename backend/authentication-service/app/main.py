from fastapi import FastAPI

from app.routes import health, login, metrics

app = FastAPI(title="Authentication Service", version="1.0.0")

app.include_router(login.router)
app.include_router(health.router)
app.include_router(metrics.router)
