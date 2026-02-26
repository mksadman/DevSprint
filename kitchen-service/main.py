from fastapi import FastAPI

app = FastAPI(title="Kitchen Service", version="1.0.0")


@app.get("/health")
async def health():
    """Liveness / readiness probe."""
    return {"status": "ok", "service": "kitchen-service"}
