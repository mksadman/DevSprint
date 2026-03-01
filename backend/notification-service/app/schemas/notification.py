from __future__ import annotations

from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, Field


class NotificationEvent(BaseModel):
    order_id: UUID
    student_id: str
    status: str


class WebSocketMessage(BaseModel):
    event: str
    payload: dict


class HealthResponse(BaseModel):
    status: str
    websocket: str


class MetricsResponse(BaseModel):
    total_messages_sent: Annotated[int, Field(ge=0)]
    active_connections: Annotated[int, Field(ge=0)]
