from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.inventory import (
    InventoryCreate,
    InventoryDelta,
    InventoryResponse,
    InventoryUpdate,
    ItemCreate,
    ItemResponse,
    ItemUpdate,
)
from app.services import inventory as inventory_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED, tags=["items"])
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    return inventory_service.create_item(db, item)


@router.get("/items", response_model=List[ItemResponse], tags=["items"])
def read_items(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    return inventory_service.list_items(db, limit=limit, offset=offset)


@router.get("/items/{item_id}", response_model=ItemResponse, tags=["items"])
def read_item(item_id: UUID, db: Session = Depends(get_db)):
    return inventory_service.get_item(db, item_id)


@router.put("/items/{item_id}", response_model=ItemResponse, tags=["items"])
def update_item(item_id: UUID, item_update: ItemCreate, db: Session = Depends(get_db)):
    return inventory_service.update_item(db, item_id, item_update)


@router.patch("/items/{item_id}", response_model=ItemResponse, tags=["items"])
def patch_item(item_id: UUID, item_update: ItemUpdate, db: Session = Depends(get_db)):
    return inventory_service.patch_item(db, item_id, item_update)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["items"])
def delete_item(item_id: UUID, db: Session = Depends(get_db)):
    inventory_service.delete_item(db, item_id)


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


@router.post(
    "/inventory/",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["inventory"],
)
def create_inventory(inventory: InventoryCreate, db: Session = Depends(get_db)):
    return inventory_service.create_inventory(db, inventory)


@router.get("/inventory/{item_id}", response_model=InventoryResponse, tags=["inventory"])
def get_inventory(item_id: UUID, db: Session = Depends(get_db)):
    return inventory_service.get_inventory(db, item_id)


@router.put("/inventory/{item_id}", response_model=InventoryResponse, tags=["inventory"])
def update_inventory_quantity(
    item_id: UUID, update_data: InventoryUpdate, db: Session = Depends(get_db)
):
    return inventory_service.update_inventory_quantity(db, item_id, update_data)


@router.patch("/inventory/{item_id}", response_model=InventoryResponse, tags=["inventory"])
def adjust_inventory_quantity(
    item_id: UUID, delta_data: InventoryDelta, db: Session = Depends(get_db)
):
    return inventory_service.adjust_inventory_quantity(db, item_id, delta_data)


@router.delete(
    "/inventory/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["inventory"],
)
def delete_inventory(item_id: UUID, db: Session = Depends(get_db)):
    inventory_service.delete_inventory(db, item_id)
