from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.inventory import Inventory, Item
from app.models.transaction import StockTransaction
from app.schemas.inventory import (
    InventoryCreate,
    InventoryDelta,
    InventoryUpdate,
    ItemCreate,
    ItemUpdate,
)


# ---------------------------------------------------------------------------
# Item operations
# ---------------------------------------------------------------------------


def create_item(db: Session, item: ItemCreate) -> Item:
    new_item = Item(name=item.name, price=item.price)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


def get_item(db: Session, item_id: UUID) -> Item:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


def list_items(db: Session, limit: int = 20, offset: int = 0) -> List[Item]:
    return db.query(Item).offset(offset).limit(limit).all()


def update_item(db: Session, item_id: UUID, item_update: ItemCreate) -> Item:
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db_item.name = item_update.name
    db_item.price = item_update.price
    db.commit()
    db.refresh(db_item)
    return db_item


def patch_item(db: Session, item_id: UUID, item_update: ItemUpdate) -> Item:
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    for key, value in item_update.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_item(db: Session, item_id: UUID) -> None:
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if db_item.inventory:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item has associated inventory",
        )
    db.delete(db_item)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete item because it is referenced by other records",
        )


# ---------------------------------------------------------------------------
# Inventory operations
# ---------------------------------------------------------------------------


def create_inventory(db: Session, inventory: InventoryCreate) -> Inventory:
    item = db.query(Item).filter(Item.id == inventory.item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    existing = db.query(Inventory).filter(Inventory.item_id == inventory.item_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory already exists for this item",
        )

    new_inventory = Inventory(item_id=inventory.item_id, quantity=inventory.quantity)
    try:
        db.add(new_inventory)
        db.commit()
        db.refresh(new_inventory)
        return new_inventory
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory creation failed due to conflict",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def get_inventory(db: Session, item_id: UUID) -> Inventory:
    inventory = db.query(Inventory).filter(Inventory.item_id == item_id).first()
    if not inventory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    return inventory


def update_inventory_quantity(db: Session, item_id: UUID, update_data: InventoryUpdate) -> Inventory:
    inventory = (
        db.query(Inventory).filter(Inventory.item_id == item_id).with_for_update().first()
    )
    if not inventory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    inventory.quantity = update_data.quantity
    inventory.version += 1
    try:
        db.commit()
        db.refresh(inventory)
        return inventory
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def adjust_inventory_quantity(db: Session, item_id: UUID, delta_data: InventoryDelta) -> Inventory:
    inventory = (
        db.query(Inventory).filter(Inventory.item_id == item_id).with_for_update().first()
    )
    if not inventory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    new_quantity = inventory.quantity + delta_data.delta
    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resulting quantity cannot be negative",
        )
    inventory.quantity = new_quantity
    inventory.version += 1
    try:
        db.commit()
        db.refresh(inventory)
        return inventory
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def delete_inventory(db: Session, item_id: UUID) -> None:
    inventory = (
        db.query(Inventory).filter(Inventory.item_id == item_id).with_for_update().first()
    )
    if not inventory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    transactions_exist = (
        db.query(StockTransaction).filter(StockTransaction.item_id == item_id).first()
    )
    if transactions_exist:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete inventory with existing stock transactions",
        )
    try:
        db.delete(inventory)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
