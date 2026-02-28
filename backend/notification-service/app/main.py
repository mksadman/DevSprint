from fastapi import FastAPI

from app.routers import health, websocket

app = FastAPI(title="Notification Service", version="1.0.0")

app.include_router(health.router)
app.include_router(websocket.router)
