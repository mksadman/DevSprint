import hashlib
import json
import logging
import time
from contextlib import contextmanager
from typing import Annotated, Callable

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db, get_session_factory
from app.models.idempotency import IdempotencyKey, IdempotencyStatus
from app.models.order import GatewayOrder, OrderStatus
from app.schemas.order import OrderRequest, OrderResponse, OrderListResponse, OrderSummary
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


@contextmanager
def _short_session(factory: Callable):
    """Open a DB session and guarantee it is closed (connection returned to pool)."""
    db = factory()
    try:
        yield db
    finally:
        db.close()


def _mark_idempotency_failed(
    db_factory: Callable, order_id, detail: str,
) -> None:
    """Update the idempotency record to FAILED in its own short-lived session."""
    with _short_session(db_factory) as db:
        idem = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.order_id == order_id)
            .first()
        )
        if idem:
            idem.status = IdempotencyStatus.FAILED.value
            idem.response_payload = {"detail": detail}
            db.commit()


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
    db_factory: Callable = Depends(get_session_factory),
) -> OrderResponse:
    start = time.perf_counter()
    metrics.increment_total_attempts()

    payload = validate_token(credentials)
    student_id: str = payload["student_id"]

    # ── Phase 1: Idempotency check (short-lived session) ───────────
    with _short_session(db_factory) as db:
        existing_key = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.order_id == request.order_id)
            .first()
        )
        if existing_key is not None:
            if existing_key.status == IdempotencyStatus.CONFIRMED.value:
                metrics.record_latency((time.perf_counter() - start) * 1000)
                return OrderResponse(order_id=request.order_id, status=OrderStatus.CONFIRMED.value)
            if existing_key.status == IdempotencyStatus.FAILED.value:
                metrics.increment_rejected()
                metrics.record_latency((time.perf_counter() - start) * 1000)
                detail = (existing_key.response_payload or {}).get("detail", "Previously rejected")
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

        idem_record = IdempotencyKey(
            order_id=request.order_id,
            request_hash=_request_hash(request),
            status=IdempotencyStatus.RECEIVED.value,
        )
        db.add(idem_record)
        db.commit()
    # ← DB connection returned to pool

    # ── Phase 2: Cache short-circuit (NO DB session held) ──────────
    cached = await get_cached_stock(request.item_id)
    if cached is not None and cached == 0:
        _mark_idempotency_failed(db_factory, request.order_id, "Item is out of stock")
        metrics.increment_cache_short_circuits()
        metrics.increment_rejected()
        metrics.record_latency((time.perf_counter() - start) * 1000)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item is out of stock",
        )

    # ── Phase 3: Stock deduction (NO DB session held) ──────────────
    try:
        stock_response = await deduct_stock(
            order_id=str(request.order_id),
            item_id=request.item_id,
            quantity=request.quantity,
        )
    except httpx.TimeoutException:
        _mark_idempotency_failed(db_factory, request.order_id, "Stock service did not respond in time")
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

        _mark_idempotency_failed(db_factory, request.order_id, str(detail))
        metrics.increment_downstream_failures()
        metrics.increment_rejected()
        metrics.record_latency((time.perf_counter() - start) * 1000)
        raise HTTPException(status_code=upstream_status, detail=detail)
    except Exception as exc:
        logger.error("Unexpected error calling stock-service: %s", exc)
        _mark_idempotency_failed(db_factory, request.order_id, "Stock service is unavailable")
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

    # ── Phase 4: Persist order + outbox event (short-lived session) ─
    with _short_session(db_factory) as db:
        order_record = GatewayOrder(
            order_id=request.order_id,
            student_id=student_id,
            item_id=request.item_id,
            quantity=request.quantity,
            status=OrderStatus.CONFIRMED.value,
        )
        db.add(order_record)

        idem = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.order_id == request.order_id)
            .first()
        )
        if idem:
            idem.status = IdempotencyStatus.CONFIRMED.value
            idem.response_payload = {
                "order_id": str(request.order_id),
                "status": OrderStatus.CONFIRMED.value,
            }

        # Outbox: event is written in the SAME transaction as the order
        publish_order_event(db, {
            "order_id": str(request.order_id),
            "item_id": request.item_id,
            "quantity": request.quantity,
            "student_id": student_id,
        })
        db.commit()
    # ← DB connection returned to pool

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


@router.get(
    "/orders",
    response_model=OrderListResponse,
    summary="List all orders for the current user",
)
async def list_orders(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    db: Session = Depends(get_db),
) -> OrderListResponse:
    payload = validate_token(credentials)
    student_id: str = payload["student_id"]

    orders = (
        db.query(GatewayOrder)
        .filter(GatewayOrder.student_id == student_id)
        .order_by(GatewayOrder.created_at.desc())
        .all()
    )

    # Enrich each order with the latest pipeline status from the shared notifications
    # table (stock/kitchen services). Falls back to PENDING when the pipeline has not
    # emitted a status event yet (i.e. order was just CONFIRMED by the gateway).
    pipeline_status_map: dict[str, str] = {}
    if orders:
        order_ids_str = [str(o.order_id) for o in orders]
        rows = db.execute(
            text(
                """
                SELECT DISTINCT ON (order_id) order_id::text AS order_id_str, status_sent
                FROM notifications
                WHERE order_id::text = ANY(:oids)
                ORDER BY order_id, sent_at DESC
                """
            ),
            {"oids": order_ids_str},
        ).fetchall()
        pipeline_status_map = {row.order_id_str: row.status_sent for row in rows}

    enriched = [
        OrderSummary(
            order_id=o.order_id,
            item_id=o.item_id,
            quantity=o.quantity,
            status=pipeline_status_map.get(str(o.order_id), "PENDING"),
            created_at=o.created_at,
        )
        for o in orders
    ]

    return OrderListResponse(orders=enriched)
