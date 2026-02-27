from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid


class OrderMessage(BaseModel):
    """Shape of the message consumed from order_queue."""
    order_id: str
    student_id: str
    items: Optional[list] = []


class StatusUpdate(BaseModel):
    """Shape of the message published to notification_queue."""
    order_id: str
    student_id: str
    status: str


class StatusHistoryResponse(BaseModel):
    id: str
    status: str
    changed_at: datetime

    class Config:
        from_attributes = True


class KitchenOrderResponse(BaseModel):
    id: str
    order_id: str
    status: str
    received_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status_history: List[StatusHistoryResponse] = []

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    database: str
    rabbitmq: str


class MetricsResponse(BaseModel):
    total_orders_processed: int
    total_failures: int
    orders_in_progress: int
    average_processing_time_ms: float
