from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.inventory import Inventory, Item
from app.models.transaction import StockTransaction
from app.schemas.stock import StockDeductRequest


def deduct_stock(db: Session, request: StockDeductRequest) -> dict:
    """
    Atomically verify and deduct stock using Optimistic Locking.
    Ensures idempotency via unique constraint on StockTransaction.
    """
    if request.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than 0",
        )

    # 1. Quick check for existing transaction (optimization)
    existing_txn = (
        db.query(StockTransaction)
        .filter(
            StockTransaction.order_id == request.order_id,
            StockTransaction.item_id == request.item_id,
        )
        .first()
    )
    if existing_txn:
        return {
            "status": "success",
            "message": "Stock already deducted",
            "transaction_id": str(existing_txn.id),
        }

    # 2. Check Item existence
    item = db.query(Item).filter(Item.id == request.item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # 3. Optimistic Locking Loop
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Read current state (No lock)
            inventory = (
                db.query(Inventory)
                .filter(Inventory.item_id == request.item_id)
                .first()
            )
            if not inventory:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Inventory record not found for this item",
                )

            # Check stock
            if inventory.quantity < request.quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Insufficient stock",
                )

            # Attempt update with version check
            current_version = inventory.version
            update_result = (
                db.query(Inventory)
                .filter(
                    Inventory.item_id == request.item_id,
                    Inventory.version == current_version,
                )
                .update(
                    {
                        "quantity": Inventory.quantity - request.quantity,
                        "version": Inventory.version + 1,
                    },
                    synchronize_session=False,
                )
            )

            if update_result == 0:
                # Version mismatch (concurrent update) -> Retry
                db.rollback()
                continue

            # Insert transaction record
            new_txn = StockTransaction(
                order_id=request.order_id,
                item_id=request.item_id,
                quantity_deducted=request.quantity,
            )
            db.add(new_txn)

            # Commit transaction
            db.commit()
            db.refresh(new_txn)
            
            # Since we used synchronize_session=False, we need to refresh inventory or calc remaining
            # But simpler to just return the calculated remaining if needed, or query again.
            # We know what we subtracted.
            remaining_stock = inventory.quantity - request.quantity
            
            return {
                "status": "success",
                "message": "Stock deducted successfully",
                "transaction_id": str(new_txn.id),
                "remaining_stock": remaining_stock,
            }

        except IntegrityError:
            # Catch race condition on StockTransaction unique constraint
            db.rollback()
            existing_txn_race = (
                db.query(StockTransaction)
                .filter(
                    StockTransaction.order_id == request.order_id,
                    StockTransaction.item_id == request.item_id,
                )
                .first()
            )
            if existing_txn_race:
                return {
                    "status": "success",
                    "message": "Stock already deducted",
                    "transaction_id": str(existing_txn_race.id),
                }
            # If IntegrityError was something else (unlikely), re-raise
            raise

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # If loop exhausts retries
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Concurrent updates detected. Please retry.",
    )


def get_transaction_by_order(db: Session, order_id: UUID) -> List[StockTransaction]:
    transactions = (
        db.query(StockTransaction)
        .filter(StockTransaction.order_id == order_id)
        .all()
    )
    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found for this order",
        )
    return transactions


def list_transactions(
    db: Session,
    item_id: Optional[UUID] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[StockTransaction]:
    query = db.query(StockTransaction)
    if item_id:
        query = query.filter(StockTransaction.item_id == item_id)
    return (
        query.order_by(StockTransaction.created_at.desc()).offset(offset).limit(limit).all()
    )
