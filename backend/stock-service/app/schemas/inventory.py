from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1)
    price: Decimal = Field(..., gt=0)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[Decimal] = Field(None, gt=0)


class ItemResponse(ItemBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryBase(BaseModel):
    quantity: int = Field(..., ge=0)


class InventoryCreate(InventoryBase):
    item_id: UUID


class InventoryUpdate(BaseModel):
    quantity: int = Field(..., ge=0)


class InventoryDelta(BaseModel):
    delta: int


class InventoryResponse(InventoryBase):
    id: UUID
    item_id: UUID
    version: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
