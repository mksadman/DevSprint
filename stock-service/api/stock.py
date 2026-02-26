from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models
import schemas

router = APIRouter(
    prefix="/stock",
    tags=["stock"]
)

@router.post("/deduct", status_code=status.HTTP_200_OK)
def deduct_stock(request: schemas.StockDeductRequest, db: Session = Depends(models.get_db)):
    """
    Deduct stock transactionally.
    Idempotent using order_id.
    """
    
    # 1. Validate input
    if request.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than 0"
        )

    # 2. Check idempotency: Check if this order_id already exists in stock_transactions for this item
    # Note: Since order_id is not unique globally (an order can have multiple items), 
    # we check for the pair (order_id, item_id).
    existing_txn = db.query(models.StockTransaction).filter(
        models.StockTransaction.order_id == request.order_id,
        models.StockTransaction.item_id == request.item_id
    ).first()

    if existing_txn:
        # Idempotent success - return 200 OK
        return {"status": "success", "message": "Stock already deducted", "transaction_id": str(existing_txn.id)}

    # 3. Check if item exists (Optional, but good for clear error)
    # Actually, we can just try to lock inventory. If inventory not found, item probably doesn't have stock record or doesn't exist.
    # The requirements say "Check if item exists -> Return 404".
    # Checking Item table first is safer.
    item = db.query(models.Item).filter(models.Item.id == request.item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # 4. Lock inventory row safely
    # We use SELECT FOR UPDATE to prevent race conditions.
    inventory = db.query(models.Inventory).filter(
        models.Inventory.item_id == request.item_id
    ).with_for_update().first()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found for this item"
        )

    # Double check idempotency inside the lock?
    # If two concurrent requests came, one might have passed the first check.
    # So we should check again or rely on the fact that we insert the transaction within the same lock scope?
    # Actually, StockTransaction is a different table. Locking Inventory doesn't lock StockTransaction reads.
    # But since we are creating a new StockTransaction, checking existence again is good practice if we want to be super safe,
    # OR we can rely on a unique constraint on (order_id, item_id). 
    # Since we didn't add the constraint (trying to minimize model changes), let's check again inside the transaction 
    # just to be sure, although strictly speaking, if we just check before commit it might be enough.
    # However, standard pattern:
    # 1. Lock resource (Inventory) -> This serializes operations on this Item.
    # 2. Check if work is already done (Idempotency check) -> Now safe because other threads waiting for lock haven't written yet.
    
    existing_txn_check = db.query(models.StockTransaction).filter(
        models.StockTransaction.order_id == request.order_id,
        models.StockTransaction.item_id == request.item_id
    ).first()

    if existing_txn_check:
        db.rollback() # Release lock
        return {"status": "success", "message": "Stock already deducted", "transaction_id": str(existing_txn_check.id)}

    # 5. Ensure quantity available
    if inventory.quantity < request.quantity:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient stock"
        )

    # 6. Deduct stock atomically
    inventory.quantity -= request.quantity
    inventory.version += 1
    # updated_at is auto-updated by SQLAlchemy onupdate hook usually, or we can force it if needed.
    # The model has `onupdate=func.now()`, so it should be fine.

    # 7. Insert stock_transactions record
    new_txn = models.StockTransaction(
        order_id=request.order_id,
        item_id=request.item_id,
        quantity_deducted=request.quantity
    )
    db.add(new_txn)

    # 8. Commit transaction
    try:
        db.commit()
        db.refresh(new_txn)
        return {"status": "success", "message": "Stock deducted successfully", "transaction_id": str(new_txn.id)}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
