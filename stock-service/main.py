from fastapi import FastAPI, Request
from api import itemCatalog, inventory, stock, transactionAudit, admin
import models
import time

app = FastAPI(title="Stock Service", version="1.0.0")

# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # ms
    
    # Update metrics in admin module
    # Note: We access the metrics dict directly. 
    # In a real app, this should be thread-safe (e.g. using locks) or use an atomic store.
    # For hackathon/MVP, simple dict update is acceptable as per rules.
    
    admin.metrics["total_requests"] += 1
    admin.metrics["total_latency_ms"] += process_time
    
    path = request.url.path
    if path not in admin.metrics["request_count_per_route"]:
        admin.metrics["request_count_per_route"][path] = 0
    admin.metrics["request_count_per_route"][path] += 1
    
    # Track deductions
    # We can infer deduction attempts from path and method
    if request.url.path == "/stock/deduct" and request.method == "POST":
        admin.metrics["total_deductions"] += 1
        if response.status_code != 200:
            admin.metrics["failed_deductions"] += 1
            
    return response

# Create tables if they don't exist
models.Base.metadata.create_all(bind=models.engine)

app.include_router(itemCatalog.router)
app.include_router(inventory.router)
app.include_router(stock.router)
app.include_router(transactionAudit.router)
app.include_router(admin.router)
