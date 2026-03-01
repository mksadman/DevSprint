import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.core.database import engine, Base
from app.models import inventory as _inventory_models  # noqa: F401
from app.models import transaction as _transaction_models  # noqa: F401
from app.routers import admin, inventory, stock
from app.services.metrics import record_deduction, record_request

# We'll import the seed function dynamically to avoid circular imports
# or path issues if not strictly necessary at top level.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    Base.metadata.create_all(bind=engine)
    
    # Seed default items if missing
    try:
        from seed_fixed_items import seed
        seed()
    except ImportError:
        pass  # In case the file is not found in the path
    except Exception as e:
        print(f"Seeding failed: {e}")
        
    yield

app = FastAPI(title="Stock Service", version="1.0.0", lifespan=lifespan)


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
