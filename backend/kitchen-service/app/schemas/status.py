from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class KitchenStatusUpdate(BaseModel):
    order_id: UUID
    status: Literal["IN_KITCHEN", "READY"]


class HealthResponse(BaseModel):
    status: str
    queue: str


class MetricsResponse(BaseModel):
    total_orders_received: Annotated[int, Field(ge=0)]
    total_orders_processed: Annotated[int, Field(ge=0)]
    average_processing_time_ms: Annotated[float, Field(ge=0)]
