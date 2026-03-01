from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inventory import Inventory, Item
from app.models.transaction import StockTransaction
from app.schemas.stock import StockDeductRequest


def deduct_stock(db: Session, request: StockDeductRequest) -> dict:
    """Atomically verify and deduct stock. Idempotent on order_id + item_id."""
    if request.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than 0",
        )

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

    item = db.query(Item).filter(Item.id == request.item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    inventory = (
        db.query(Inventory)
        .filter(Inventory.item_id == request.item_id)
        .with_for_update()
        .first()
    )
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found for this item",
        )

    existing_txn_check = (
        db.query(StockTransaction)
        .filter(
            StockTransaction.order_id == request.order_id,
            StockTransaction.item_id == request.item_id,
        )
        .first()
    )
    if existing_txn_check:
        db.rollback()
        return {
            "status": "success",
            "message": "Stock already deducted",
            "transaction_id": str(existing_txn_check.id),
        }

    if inventory.quantity < request.quantity:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient stock",
        )

    inventory.quantity -= request.quantity
    inventory.version += 1

    new_txn = StockTransaction(
        order_id=request.order_id,
        item_id=request.item_id,
        quantity_deducted=request.quantity,
    )
    db.add(new_txn)

    try:
        db.commit()
        db.refresh(new_txn)
        remaining_stock = inventory.quantity
        return {
            "status": "success",
            "message": "Stock deducted successfully",
            "transaction_id": str(new_txn.id),
            "remaining_stock": remaining_stock,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
