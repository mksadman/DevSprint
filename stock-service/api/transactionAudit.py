from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
import models
import schemas

router = APIRouter(
    prefix="/transactions",
    tags=["audit"]
)

@router.get("/{order_id}", response_model=List[schemas.StockTransactionResponse])
def get_transaction_by_order(order_id: UUID, db: Session = Depends(models.get_db)):
    """
    Retrieve transaction(s) for a specific order.
    Note: An order can have multiple items, so multiple transactions.
    """
    transactions = db.query(models.StockTransaction).filter(
        models.StockTransaction.order_id == order_id
    ).all()

    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found for this order"
        )
    
    return transactions

@router.get("/", response_model=List[schemas.StockTransactionResponse])
def list_transactions(
    item_id: Optional[UUID] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(models.get_db)
):
    """
    List stock transactions with optional filters.
    Paginated results. Ordered by created_at DESC.
    """
    query = db.query(models.StockTransaction)

    if item_id:
        query = query.filter(models.StockTransaction.item_id == item_id)

    # Order by created_at DESC
    query = query.order_by(models.StockTransaction.created_at.desc())

    # Pagination
    transactions = query.offset(offset).limit(limit).all()

    return transactions
