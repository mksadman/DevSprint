from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID

import models
import schemas

router = APIRouter(tags=["items"])

@router.post("/items", response_model=schemas.ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: schemas.ItemCreate, db: Session = Depends(models.get_db)):
    """Create a new item."""
    new_item = models.Item(name=item.name, price=item.price)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item



@router.get("/items", response_model=List[schemas.ItemResponse])
def read_items(
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(models.get_db)
):
    """Return list of all items."""
    items = db.query(models.Item).offset(offset).limit(limit).all()
    return items



@router.get("/items/{item_id}", response_model=schemas.ItemResponse)
def read_item(item_id: UUID, db: Session = Depends(models.get_db)):
    """Return single item by UUID."""
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item



@router.put("/items/{item_id}", response_model=schemas.ItemResponse)
def update_item(item_id: UUID, item_update: schemas.ItemCreate, db: Session = Depends(models.get_db)):
    """Full update (replace name and price)."""
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    db_item.name = item_update.name
    db_item.price = item_update.price
    
    db.commit()
    db.refresh(db_item)
    return db_item



@router.patch("/items/{item_id}", response_model=schemas.ItemResponse)
def patch_item(item_id: UUID, item_update: schemas.ItemUpdate, db: Session = Depends(models.get_db)):
    """Partial update."""
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item




@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: UUID, db: Session = Depends(models.get_db)):
    """Delete item."""
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        # Idempotent delete usually returns 204 even if not found, but requirement says "HTTP 404 if item does not exist" 
        # Wait, requirements for DELETE say "Return 204 on success". It doesn't explicitly say 404 if not found, 
        # but typically REST does. However, usually idempotent is better.
        # Let's check constraints: "HTTP 404 if item does not exist" was for PUT/PATCH.
        # But commonly DELETE returns 404 if not found. I'll stick to 404 if not found to be safe, or just return 204 if already gone.
        # Re-reading: "Delete item. If inventory exists for item, reject with 409 Conflict. Do NOT cascade delete inventory automatically. Return 204 on success."
        # It doesn't mention 404. But standard CRUD does. I'll return 404 if not found.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Check for inventory
    # Using relationship or direct query
    # The relationship is `inventory = relationship("Inventory", uselist=False, back_populates="item")`
    # So we can check `db_item.inventory`
    
    if db_item.inventory:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Item has associated inventory")
    
    # Also check stock_transactions? Requirement says "If inventory exists...". 
    # Usually stock transactions are historical records, so deleting item might break FK.
    # "Do NOT cascade delete inventory automatically".
    # If there are transactions, we might also need to block delete if there is FK constraint.
    # The model `StockTransaction` has `item_id = Column(UUID(as_uuid=True), ForeignKey('items.id'), nullable=False)`
    # So if transactions exist, delete will fail with IntegrityError.
    # I should check for transactions too or let IntegrityError handle it.
    # But requirement only mentions "If inventory exists".
    # I'll check inventory explicitly. For transactions, I'll let DB constraint handle it or check it.
    # Given "Do not introduce unnecessary complexity", I'll just check inventory as requested.
    # If transactions exist, the DB will raise IntegrityError, which I should catch or let bubble up as 500 (or better 409).
    # But to be safe and clean, I should probably check transactions too if I want to give a nice error.
    # However, for now, I'll stick to the explicit requirement about inventory.
    
    db.delete(db_item)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # If it's integrity error (e.g. transactions), return 409
        # But I need to import IntegrityError
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete item because it is referenced by other records (e.g. transactions)")

    return None
