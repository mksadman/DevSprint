import time

from fastapi import FastAPI, Request

from app.core.database import engine
from app.models import inventory as _inventory_models  # noqa: F401 — registers models
from app.models import transaction as _transaction_models  # noqa: F401 — registers models
from app.core.database import Base
from app.routers import admin, inventory, stock
from app.services.metrics import record_deduction, record_request

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Stock Service", version="1.0.0")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000

    record_request(request.url.path, process_time)

    if request.url.path == "/stock/deduct" and request.method == "POST":
        record_deduction(failed=response.status_code != 200)

    return response


app.include_router(inventory.router)
app.include_router(stock.router)
app.include_router(admin.router)
