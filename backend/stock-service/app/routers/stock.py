from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import INTERNAL_API_KEY
from app.core.database import get_db
from app.schemas.stock import StockDeductRequest, StockTransactionResponse
from app.services import stock as stock_service
from app.services.auth import require_auth

router = APIRouter(tags=["stock"])


def _require_internal_key(
    x_internal_key: str | None = Header(None, alias="X-Internal-Key"),
) -> None:
    """Verify the caller provides the correct internal service-to-service key."""
    if x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )


@router.post("/stock/deduct", status_code=200)
def deduct_stock(
    request: StockDeductRequest,
    db: Session = Depends(get_db),
    _key: None = Depends(_require_internal_key),
):
    return stock_service.deduct_stock(db, request)


@router.get("/transactions/{order_id}", response_model=List[StockTransactionResponse], tags=["audit"])
def get_transaction_by_order(order_id: UUID, db: Session = Depends(get_db), _user: dict[str, Any] = Depends(require_auth)):
    return stock_service.get_transaction_by_order(db, order_id)


@router.get("/transactions/", response_model=List[StockTransactionResponse], tags=["audit"])
def list_transactions(
    item_id: Optional[UUID] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_auth),
):
    return stock_service.list_transactions(db, item_id=item_id, limit=limit, offset=offset)
