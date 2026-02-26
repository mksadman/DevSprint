from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal

# --- Item Schemas ---

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the item")
    price: Decimal = Field(..., gt=0, description="Price of the item")

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Name of the item")
    price: Optional[Decimal] = Field(None, gt=0, description="Price of the item")

class ItemResponse(ItemBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




# --- Inventory Schemas ---

class InventoryBase(BaseModel):
    quantity: int = Field(..., ge=0, description="Available stock quantity")

class InventoryCreate(InventoryBase):
    item_id: UUID

class InventoryUpdate(BaseModel):
    quantity: int = Field(..., ge=0, description="New stock quantity")

class InventoryResponse(InventoryBase):
    id: UUID
    item_id: UUID
    version: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




# --- Stock Transaction Schemas ---

class StockTransactionBase(BaseModel):
    order_id: UUID
    item_id: UUID
    quantity_deducted: int = Field(..., gt=0, description="Quantity deducted from stock")

class StockTransactionCreate(StockTransactionBase):
    pass

class StockTransactionResponse(StockTransactionBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
