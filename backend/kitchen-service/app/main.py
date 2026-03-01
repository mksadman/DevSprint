from fastapi import FastAPI

from app.routers import queue

app = FastAPI(title="Kitchen Service", version="1.0.0")

app.include_router(queue.router)
