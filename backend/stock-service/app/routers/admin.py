from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import check_db_health, get_db
from app.services.metrics import get_snapshot

router = APIRouter(tags=["admin"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    if check_db_health(db):
        return {"status": "ok", "database": "connected"}
    return Response(
        content='{"status": "error", "database": "unreachable"}',
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        media_type="application/json",
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
