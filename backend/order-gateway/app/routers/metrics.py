from fastapi import APIRouter

from app.schemas.metrics import MetricsResponse
from app.services.metrics import metrics

router = APIRouter(tags=["Ops"])


@router.get("/metrics", response_model=MetricsResponse, summary="In-process metrics")
async def get_metrics() -> MetricsResponse:
    return MetricsResponse(**metrics.snapshot())
