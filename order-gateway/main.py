from fastapi import FastAPI

app = FastAPI(title="Order Gateway", version="1.0.0")


@app.get("/health")
async def health():
    """Liveness / readiness probe."""
    return {"status": "ok", "service": "order-gateway"}
