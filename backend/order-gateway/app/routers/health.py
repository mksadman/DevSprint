from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi import status

from app.services.cache import redis_ping
from app.services.order import stock_health_ping

router = APIRouter(tags=["Ops"])


@router.get("/health", summary="Dependency health check")
async def health() -> JSONResponse:
    redis_ok = await redis_ping()
    stock_ok = await stock_health_ping()

    dependencies = {
        "redis": "ok" if redis_ok else "unreachable",
        "stock-service": "ok" if stock_ok else "unreachable",
    }
    overall = "ok" if (redis_ok and stock_ok) else "degraded"
    http_status = (
        status.HTTP_200_OK
        if (redis_ok and stock_ok)
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(
        status_code=http_status,
        content={"status": overall, "dependencies": dependencies},
    )
