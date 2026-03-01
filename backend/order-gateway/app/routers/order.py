import hashlib
import json
import logging
import time
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.idempotency import IdempotencyKey, IdempotencyStatus
from app.models.order import GatewayOrder, OrderStatus
from app.schemas.order import OrderRequest, OrderResponse
from app.services.auth import validate_token
from app.services.cache import get_cached_stock, set_cached_stock
from app.services.metrics import metrics
from app.services.order import deduct_stock
from app.services.queue import publish_order_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Orders"])
_bearer_scheme = HTTPBearer(auto_error=False)


def _request_hash(request: OrderRequest) -> str:
    """Compute a stable SHA-256 digest for the canonical request body."""
    canonical = json.dumps(
        {"order_id": str(request.order_id), "item_id": request.item_id, "quantity": request.quantity},
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@router.post(
    "/order",
    response_model=OrderResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Place an order",
)
async def place_order(
    request: OrderRequest,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    db: Session = Depends(get_db),
) -> OrderResponse:
    start = time.perf_counter()
    metrics.increment_total_attempts()

    payload = validate_token(credentials)
    student_id: str = payload["student_id"]

    # ── Idempotency check ──────────────────────────────────────────────
    existing_key = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.order_id == request.order_id)
        .first()
    )
    if existing_key is not None:
        # Already processed — return the stored response without re-deducting
        if existing_key.status == IdempotencyStatus.CONFIRMED.value:
            metrics.record_latency((time.perf_counter() - start) * 1000)
            return OrderResponse(order_id=request.order_id, status=OrderStatus.CONFIRMED.value)
        if existing_key.status == IdempotencyStatus.FAILED.value:
            metrics.increment_rejected()
            metrics.record_latency((time.perf_counter() - start) * 1000)
            detail = (existing_key.response_payload or {}).get("detail", "Previously rejected")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    # ── Create idempotency record (RECEIVED) ───────────────────────────
    idem_record = IdempotencyKey(
        order_id=request.order_id,
        request_hash=_request_hash(request),
        status=IdempotencyStatus.RECEIVED.value,
    )
    db.add(idem_record)
    db.flush()  # write to DB so a concurrent request sees it

    payload = validate_token(credentials)
    student_id: str = payload["student_id"]

    # ── Cache short-circuit ──────────────────────────────────────────────
    cached = await get_cached_stock(request.item_id)
    if cached is not None and cached == 0:
        idem_record.status = IdempotencyStatus.FAILED.value
        idem_record.response_payload = {"detail": "Item is out of stock"}
        db.commit()
        metrics.increment_cache_short_circuits()
        metrics.increment_rejected()
        metrics.record_latency((time.perf_counter() - start) * 1000)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item is out of stock",
        )

    # ── Stock deduction ────────────────────────────────────────────────
    try:
        stock_response = await deduct_stock(
            order_id=str(request.order_id),
            item_id=request.item_id,
            quantity=request.quantity,
        )
    except httpx.TimeoutException:
        idem_record.status = IdempotencyStatus.FAILED.value
        idem_record.response_payload = {"detail": "Stock service did not respond in time"}
        db.commit()
        metrics.increment_downstream_failures()
        metrics.increment_rejected()
        metrics.record_latency((time.perf_counter() - start) * 1000)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Stock service did not respond in time",
        )
    except httpx.HTTPStatusError as exc:
        upstream_status = exc.response.status_code
        try:
            detail = exc.response.json()
        except Exception:
            detail = exc.response.text

        if upstream_status == status.HTTP_409_CONFLICT:
            await set_cached_stock(request.item_id, 0)

        idem_record.status = IdempotencyStatus.FAILED.value
        idem_record.response_payload = {"detail": str(detail)}
        db.commit()
        metrics.increment_downstream_failures()
        metrics.increment_rejected()
        metrics.record_latency((time.perf_counter() - start) * 1000)
        raise HTTPException(status_code=upstream_status, detail=detail)
    except Exception as exc:
        logger.error("Unexpected error calling stock-service: %s", exc)
        idem_record.status = IdempotencyStatus.FAILED.value
        idem_record.response_payload = {"detail": "Stock service is unavailable"}
        db.commit()
        metrics.increment_downstream_failures()
        metrics.increment_rejected()
        metrics.record_latency((time.perf_counter() - start) * 1000)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stock service is unavailable",
        )

    remaining = stock_response.get("remaining_stock")
    if remaining is not None:
        await set_cached_stock(request.item_id, int(remaining))

    # ── Publish to kitchen (fire-and-forget) ───────────────────────────
    publish_order_event(
        {
            "order_id": str(request.order_id),
            "item_id": request.item_id,
            "quantity": request.quantity,
            "student_id": student_id,
        }
    )

    # ── Persist order & confirm idempotency ────────────────────────────
    order_record = GatewayOrder(
        order_id=request.order_id,
        student_id=student_id,
        item_id=request.item_id,
        quantity=request.quantity,
        status=OrderStatus.CONFIRMED.value,
    )
    db.add(order_record)
    idem_record.status = IdempotencyStatus.CONFIRMED.value
    idem_record.response_payload = {"order_id": str(request.order_id), "status": OrderStatus.CONFIRMED.value}
    db.commit()

    elapsed_ms = (time.perf_counter() - start) * 1000
    metrics.increment_successful()
    metrics.record_latency(elapsed_ms)

    logger.info(
        "Order accepted: order_id=%s student_id=%s latency=%.2f ms",
        request.order_id,
        student_id,
        elapsed_ms,
    )
    return OrderResponse(order_id=request.order_id, status=OrderStatus.CONFIRMED.value)
