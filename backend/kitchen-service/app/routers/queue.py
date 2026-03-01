from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.schemas.event import KitchenOrderEvent
from app.schemas.status import HealthResponse, KitchenStatusUpdate, MetricsResponse
from app.services.processor import enqueue_order, get_metrics_snapshot, get_order_status

router = APIRouter(tags=["queue"])


@router.post("/orders", status_code=status.HTTP_202_ACCEPTED)
async def receive_order(event: KitchenOrderEvent) -> dict:
    """Accept an order event from the order-gateway and enqueue it for processing."""
    record = enqueue_order(event)
    return {"status": "queued", "order_id": record["order_id"]}


@router.get("/orders/{order_id}/status", response_model=KitchenStatusUpdate)
async def get_order_status_route(order_id: UUID) -> KitchenStatusUpdate:
    """Return the current kitchen status for an order."""
    record = get_order_status(order_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return KitchenStatusUpdate(order_id=order_id, status=record["status"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness / readiness probe."""
    return HealthResponse(status="ok", queue="ready")


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    """Expose kitchen processing counters."""
    return MetricsResponse(**get_metrics_snapshot())
