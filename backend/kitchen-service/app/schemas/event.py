from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel


class KitchenOrderEvent(BaseModel):
    order_id: UUID
    item_id: str
    quantity: int
    student_id: str
