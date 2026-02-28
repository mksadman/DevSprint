import logging
import time
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.order import OrderStatus
from app.schemas.order import OrderRequest, OrderResponse
from app.services.auth import validate_token
from app.services.cache import get_cached_stock, set_cached_stock
from app.services.metrics import metrics
from app.services.order import deduct_stock
from app.services.queue import publish_order_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Orders"])
_bearer_scheme = HTTPBearer(auto_error=False)


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
) -> OrderResponse:
    start = time.perf_counter()
    metrics.increment_total_attempts()

    payload = validate_token(credentials)
    student_id: str = payload["student_id"]

    cached = await get_cached_stock(request.item_id)
    if cached is not None and cached == 0:
        metrics.increment_cache_short_circuits()
        metrics.increment_rejected()
        metrics.record_latency((time.perf_counter() - start) * 1000)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item is out of stock",
        )

    try:
        stock_response = await deduct_stock(
            order_id=str(request.order_id),
            item_id=request.item_id,
            quantity=request.quantity,
        )
    except httpx.TimeoutException:
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

        metrics.increment_downstream_failures()
        metrics.increment_rejected()
        metrics.record_latency((time.perf_counter() - start) * 1000)
        raise HTTPException(status_code=upstream_status, detail=detail)
    except Exception as exc:
        logger.error("Unexpected error calling stock-service: %s", exc)
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

    publish_order_event(
        {
            "order_id": str(request.order_id),
            "item_id": request.item_id,
            "quantity": request.quantity,
            "student_id": student_id,
        }
    )

    elapsed_ms = (time.perf_counter() - start) * 1000
    metrics.increment_successful()
    metrics.record_latency(elapsed_ms)

    logger.info(
        "Order accepted: order_id=%s student_id=%s latency=%.2f ms",
        request.order_id,
        student_id,
        elapsed_ms,
    )
    return OrderResponse(order_id=request.order_id, status=OrderStatus.CONFIRMED)
