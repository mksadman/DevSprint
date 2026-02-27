from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from datetime import datetime
import models
import schemas
from typing import List

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"]
)

@router.post("/", response_model=schemas.InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory(inventory: schemas.InventoryCreate, db: Session = Depends(models.get_db)):
    """
    Create inventory record for an existing item.
    """
    # Check if item exists
    item = db.query(models.Item).filter(models.Item.id == inventory.item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # Check if inventory already exists for this item
    existing_inventory = db.query(models.Inventory).filter(models.Inventory.item_id == inventory.item_id).first()
    if existing_inventory:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory already exists for this item"
        )

    new_inventory = models.Inventory(
        item_id=inventory.item_id,
        quantity=inventory.quantity
    )
    
    try:
        db.add(new_inventory)
        db.commit()
        db.refresh(new_inventory)
        return new_inventory
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory creation failed due to conflict"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{item_id}", response_model=schemas.InventoryResponse)
def get_inventory(item_id: UUID, db: Session = Depends(models.get_db)):
    """
    Return inventory details for given item.
    """
    inventory = db.query(models.Inventory).filter(models.Inventory.item_id == item_id).first()
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )
    return inventory

@router.put("/{item_id}", response_model=schemas.InventoryResponse)
def update_inventory_quantity(item_id: UUID, update_data: schemas.InventoryUpdate, db: Session = Depends(models.get_db)):
    """
    Replace full quantity value.
    """
    inventory = db.query(models.Inventory).filter(models.Inventory.item_id == item_id).with_for_update().first()
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )

    inventory.quantity = update_data.quantity
    inventory.version += 1
    # updated_at is handled by onupdate in model, but let's be explicit if needed. 
    # SQLAlchemy onupdate=func.now() handles it on DB side, but for object refresh it might be needed.
    # However, let's rely on refresh or manual set if we want consistent return.
    # The requirement says "Must update updated_at". The model definition has onupdate=func.now(), so it should work.
    
    try:
        db.commit()
        db.refresh(inventory)
        return inventory
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.patch("/{item_id}", response_model=schemas.InventoryResponse)
def adjust_inventory_quantity(item_id: UUID, delta_data: schemas.InventoryDelta, db: Session = Depends(models.get_db)):
    """
    Adjust stock by delta.
    """
    # Use with_for_update for pessimistic locking to prevent race conditions during read-modify-write
    # Optimistic locking (version) is also required.
    
    inventory = db.query(models.Inventory).filter(models.Inventory.item_id == item_id).with_for_update().first()
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )

    new_quantity = inventory.quantity + delta_data.delta
    
    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resulting quantity cannot be negative"
        )

    inventory.quantity = new_quantity
    inventory.version += 1
    
    try:
        db.commit()
        db.refresh(inventory)
        return inventory
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(item_id: UUID, db: Session = Depends(models.get_db)):
    """
    Delete inventory record.
    """
    inventory = db.query(models.Inventory).filter(models.Inventory.item_id == item_id).with_for_update().first()
    
    if not inventory:
        # If not found, standard REST practice for DELETE is 204 or 404. 
        # Requirement says "HTTP 404 if inventory not found" implicitly? 
        # Actually requirement doesn't explicitly say for DELETE what if not found.
        # But for other endpoints it says 404. I'll return 404 for consistency if it doesn't exist.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )

    # Check for stock transactions
    # The relationship is on Item, but we need to check if there are transactions for this item.
    # The requirement says "Only allowed if no stock_transactions exist for this item."
    
    # We can query StockTransaction directly.
    transactions_exist = db.query(models.StockTransaction).filter(models.StockTransaction.item_id == item_id).first()
    
    if transactions_exist:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete inventory with existing stock transactions"
        )

    try:
        db.delete(inventory)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
