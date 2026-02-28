from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.stock import StockDeductRequest, StockTransactionResponse
from app.services import stock as stock_service

router = APIRouter(tags=["stock"])


@router.post("/stock/deduct", status_code=200)
def deduct_stock(request: StockDeductRequest, db: Session = Depends(get_db)):
    return stock_service.deduct_stock(db, request)


@router.get("/transactions/{order_id}", response_model=List[StockTransactionResponse], tags=["audit"])
def get_transaction_by_order(order_id: UUID, db: Session = Depends(get_db)):
    return stock_service.get_transaction_by_order(db, order_id)


@router.get("/transactions/", response_model=List[StockTransactionResponse], tags=["audit"])
def list_transactions(
    item_id: Optional[UUID] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return stock_service.list_transactions(db, item_id=item_id, limit=limit, offset=offset)
