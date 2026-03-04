import asyncio
import os

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import check_db_health, get_db
from app.services.metrics import get_snapshot
from app.schemas.health import HealthResponse

router = APIRouter(tags=["admin"])


@router.post("/chaos/kill", summary="Chaos: kill this service process")
async def chaos_kill() -> dict:
    """Terminate the process after returning a response. Used by the Admin chaos panel."""
    async def _exit():
        await asyncio.sleep(0.5)
        os._exit(1)
    asyncio.create_task(_exit())
    return {"status": "dying", "service": "stock-service"}


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    db_ok = check_db_health(db)
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "unreachable"
    )


@router.get("/metrics")
def get_metrics():
    snapshot = get_snapshot()
    avg_latency = snapshot.pop("average_latency_ms")
    lines = [
        f"total_requests {snapshot['total_requests']}",
        f"total_deductions {snapshot['total_deductions']}",
        f"failed_deductions {snapshot['failed_deductions']}",
        f"average_latency_ms {avg_latency:.2f}",
    ]
    for route, count in snapshot["request_count_per_route"].items():
        lines.append(f'request_count{{path="{route}"}} {count}')
    return Response(content="\n".join(lines), media_type="text/plain")
