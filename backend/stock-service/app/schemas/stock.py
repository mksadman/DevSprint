from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime


class StockDeductRequest(BaseModel):
    order_id: UUID
    item_id: UUID
    quantity: int = Field(..., gt=0)


class StockTransactionBase(BaseModel):
    order_id: UUID
    item_id: UUID
    quantity_deducted: int = Field(..., gt=0)


class StockTransactionCreate(StockTransactionBase):
    pass


class StockTransactionResponse(StockTransactionBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
