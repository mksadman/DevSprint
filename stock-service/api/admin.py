from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import models
import time

router = APIRouter(
    tags=["admin"]
)

# In-memory metrics storage
# Using simple dictionary for counters
metrics = {
    "total_requests": 0,
    "total_deductions": 0,
    "failed_deductions": 0,
    "total_latency_ms": 0.0,
    "request_count_per_route": {}
}

@router.get("/health")
def health_check(db: Session = Depends(models.get_db)):
    """
    Liveness + readiness probe.
    Checks DB connectivity.
    """
    try:
        # Lightweight DB check
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return Response(
            content='{"status": "error", "database": "unreachable"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )

@router.get("/metrics")
def get_metrics():
    """
    Expose operational metrics in Prometheus-style plain text format.
    """
    avg_latency = 0.0
    if metrics["total_requests"] > 0:
        avg_latency = metrics["total_latency_ms"] / metrics["total_requests"]
    
    lines = [
        f"total_requests {metrics['total_requests']}",
        f"total_deductions {metrics['total_deductions']}",
        f"failed_deductions {metrics['failed_deductions']}",
        f"average_latency_ms {avg_latency:.2f}"
    ]
    
    # Add per route metrics if needed, requirement says "request_count_per_route" in list 
    # but example output didn't show it. I'll add it as it's useful.
    # Format: request_count{path="/foo"} 10
    for route, count in metrics["request_count_per_route"].items():
        lines.append(f'request_count{{path="{route}"}} {count}')
    
    return Response(content="\n".join(lines), media_type="text/plain")
