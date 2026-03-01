from __future__ import annotations

from datetime import datetime
from typing import Literal, Annotated
from uuid import UUID
from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    order_id: UUID
    item_id: Annotated[str, Field(min_length=1)]
    quantity: Annotated[int, Field(ge=1)]


class OrderResponse(BaseModel):
    order_id: UUID
    status: Literal["CONFIRMED"]


class OrderSummary(BaseModel):
    order_id: UUID
    item_id: str
    quantity: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    orders: list[OrderSummary]


class OrderErrorResponse(BaseModel):
    detail: str
