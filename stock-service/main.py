from fastapi import FastAPI
from api import itemCatalog, inventory
import models

app = FastAPI(title="Stock Service", version="1.0.0")

# Create tables if they don't exist
models.Base.metadata.create_all(bind=models.engine)

app.include_router(itemCatalog.router)
app.include_router(inventory.router)

@app.get("/health")
async def health():
    """Liveness / readiness probe."""
    return {"status": "ok", "service": "stock-service"}
