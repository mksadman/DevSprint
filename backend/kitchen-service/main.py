from fastapi import FastAPI, Depends, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import asynccontextmanager
import aio_pika
import asyncio
import json
import time
import random
import logging
import os
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Optional

import models
from models import KitchenOrder, OrderStatusHistory, Base, get_db
from schemas import (
    OrderMessage, StatusUpdate, KitchenOrderResponse,
    StatusHistoryResponse, HealthResponse,
)

logger = logging.getLogger("kitchen-service")
logging.basicConfig(level=logging.INFO)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
ORDER_QUEUE = "order_queue"
NOTIFICATION_QUEUE = "notification_queue"

# ---------------------------------------------------------------------------
# In-memory metrics
# ---------------------------------------------------------------------------
metrics = {
    "total_requests": 0,
    "total_orders_processed": 0,
    "total_failures": 0,
    "orders_in_progress": 0,
    "total_processing_time_ms": 0.0,
    "total_latency_ms": 0.0,
    "request_count_per_route": {},
}

# RabbitMQ connection / channel (set at startup)
_rmq_connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
_rmq_channel: Optional[aio_pika.abc.AbstractChannel] = None
_consumer_task: Optional[asyncio.Task] = None


# ---------------------------------------------------------------------------
# RabbitMQ helpers
# ---------------------------------------------------------------------------
async def get_rmq_channel() -> Optional[aio_pika.abc.AbstractChannel]:
    return _rmq_channel


async def publish_notification(channel: aio_pika.abc.AbstractChannel, update: StatusUpdate):
    """Publish a status-update message to the notification queue."""
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(update.model_dump()).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=NOTIFICATION_QUEUE,
    )
    logger.info(f"Published notification: order={update.order_id} status={update.status}")


def _record_status(db: Session, kitchen_order: KitchenOrder, new_status: str):
    """Update the kitchen order status and append a history entry."""
    kitchen_order.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == "In Kitchen":
        kitchen_order.started_at = now
    elif new_status == "Ready":
        kitchen_order.completed_at = now

    db.add(OrderStatusHistory(
        kitchen_order_id=kitchen_order.id,
        status=new_status,
        changed_at=now,
    ))
    db.commit()
    db.refresh(kitchen_order)


async def _process_order(message: aio_pika.abc.AbstractIncomingMessage):
    """Process a single order message from the queue."""
    async with message.process():  # auto-ack on success, nack on exception
        start = time.time()
        try:
            body = json.loads(message.body.decode())
            order_msg = OrderMessage(**body)
            logger.info(f"Received order: {order_msg.order_id}")

            db = models.SessionLocal()
            try:
                # --- Idempotency check ---
                existing = (
                    db.query(KitchenOrder)
                    .filter(KitchenOrder.order_id == order_msg.order_id)
                    .first()
                )
                if existing:
                    logger.info(f"Duplicate order {order_msg.order_id} — skipping")
                    return

                # --- Create kitchen order ---
                kitchen_order = KitchenOrder(
                    order_id=order_msg.order_id,
                    status="In Kitchen",
                    received_at=datetime.now(timezone.utc),
                    started_at=datetime.now(timezone.utc),
                )
                db.add(kitchen_order)
                db.commit()
                db.refresh(kitchen_order)

                # Record "In Kitchen" history
                db.add(OrderStatusHistory(
                    kitchen_order_id=kitchen_order.id,
                    status="In Kitchen",
                    changed_at=datetime.now(timezone.utc),
                ))
                db.commit()

                metrics["orders_in_progress"] += 1

                # Notify: In Kitchen
                channel = await get_rmq_channel()
                if channel:
                    await publish_notification(channel, StatusUpdate(
                        order_id=order_msg.order_id,
                        student_id=order_msg.student_id,
                        status="In Kitchen",
                    ))

                # --- Simulate cooking (3-7s) ---
                cook_time = random.uniform(3, 7)
                await asyncio.sleep(cook_time)

                # --- Mark Ready ---
                _record_status(db, kitchen_order, "Ready")

                metrics["orders_in_progress"] -= 1
                metrics["total_orders_processed"] += 1
                elapsed = (time.time() - start) * 1000
                metrics["total_processing_time_ms"] += elapsed

                # Notify: Ready
                if channel:
                    await publish_notification(channel, StatusUpdate(
                        order_id=order_msg.order_id,
                        student_id=order_msg.student_id,
                        status="Ready",
                    ))

                logger.info(f"Order {order_msg.order_id} ready (cooked {cook_time:.1f}s)")

            finally:
                db.close()

        except Exception:
            metrics["total_failures"] += 1
            logger.exception("Failed to process order")
            raise  # triggers nack so message is re-queued


async def _consume_orders():
    """Long-running background task: consume from order_queue."""
    global _rmq_connection, _rmq_channel

    while True:
        try:
            _rmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            _rmq_channel = await _rmq_connection.channel()
            await _rmq_channel.set_qos(prefetch_count=10)

            # Declare queues (idempotent)
            order_q = await _rmq_channel.declare_queue(ORDER_QUEUE, durable=True)
            await _rmq_channel.declare_queue(NOTIFICATION_QUEUE, durable=True)

            logger.info("Connected to RabbitMQ — consuming order_queue")
            await order_q.consume(_process_order)

            # Keep running until connection drops
            await asyncio.Future()  # block forever

        except asyncio.CancelledError:
            logger.info("Consumer cancelled — shutting down")
            break
        except Exception:
            logger.exception("RabbitMQ connection lost — reconnecting in 5s")
            await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=models.engine)
    logger.info("Database tables created")

    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_orders())

    yield

    # Shutdown
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    if _rmq_connection and not _rmq_connection.is_closed:
        await _rmq_connection.close()
    logger.info("Kitchen service shut down")


app = FastAPI(title="Kitchen Service", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# HTTP Metrics middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000

    metrics["total_requests"] += 1
    metrics["total_latency_ms"] += elapsed

    path = request.url.path
    metrics["request_count_per_route"][path] = (
        metrics["request_count_per_route"].get(path, 0) + 1
    )
    return response


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Check DB + RabbitMQ connectivity."""
    db_ok = True
    rmq_ok = _rmq_connection is not None and not _rmq_connection.is_closed

    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    if db_ok and rmq_ok:
        return {
            "status": "ok",
            "database": "connected",
            "rabbitmq": "connected",
        }

    return Response(
        content=json.dumps({
            "status": "error",
            "database": "connected" if db_ok else "unreachable",
            "rabbitmq": "connected" if rmq_ok else "unreachable",
        }),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        media_type="application/json",
    )


@app.get("/metrics")
def get_metrics():
    """Prometheus-style plain-text metrics."""
    avg_processing = 0.0
    if metrics["total_orders_processed"] > 0:
        avg_processing = metrics["total_processing_time_ms"] / metrics["total_orders_processed"]

    avg_latency = 0.0
    if metrics["total_requests"] > 0:
        avg_latency = metrics["total_latency_ms"] / metrics["total_requests"]

    lines = [
        f"total_orders_processed {metrics['total_orders_processed']}",
        f"total_failures {metrics['total_failures']}",
        f"orders_in_progress {metrics['orders_in_progress']}",
        f"average_processing_time_ms {avg_processing:.2f}",
        f"total_requests {metrics['total_requests']}",
        f"average_latency_ms {avg_latency:.2f}",
    ]
    for route, count in metrics["request_count_per_route"].items():
        lines.append(f'request_count{{path="{route}"}} {count}')

    return Response(content="\n".join(lines), media_type="text/plain")


@app.get("/orders", response_model=list[KitchenOrderResponse])
def list_orders(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List kitchen orders, optionally filtered by status."""
    q = db.query(KitchenOrder)
    if status_filter:
        q = q.filter(KitchenOrder.status == status_filter)
    orders = q.order_by(KitchenOrder.received_at.desc()).all()
    return [_order_to_response(o) for o in orders]


@app.get("/orders/{order_id}", response_model=KitchenOrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get a kitchen order by its gateway order_id."""
    try:
        uid = uuid_mod.UUID(order_id)
    except ValueError:
        return Response(
            content=json.dumps({"detail": "Invalid order_id format"}),
            status_code=400,
            media_type="application/json",
        )
    order = (
        db.query(KitchenOrder)
        .filter(KitchenOrder.order_id == uid)
        .first()
    )
    if not order:
        return Response(
            content=json.dumps({"detail": "Order not found"}),
            status_code=404,
            media_type="application/json",
        )
    return _order_to_response(order)


@app.get("/orders/{order_id}/history", response_model=list[StatusHistoryResponse])
def get_order_history(order_id: str, db: Session = Depends(get_db)):
    """Get the full status-transition history for an order."""
    try:
        uid = uuid_mod.UUID(order_id)
    except ValueError:
        return Response(
            content=json.dumps({"detail": "Invalid order_id format"}),
            status_code=400,
            media_type="application/json",
        )
    order = (
        db.query(KitchenOrder)
        .filter(KitchenOrder.order_id == uid)
        .first()
    )
    if not order:
        return Response(
            content=json.dumps({"detail": "Order not found"}),
            status_code=404,
            media_type="application/json",
        )
    history = (
        db.query(OrderStatusHistory)
        .filter(OrderStatusHistory.kitchen_order_id == order.id)
        .order_by(OrderStatusHistory.changed_at.asc())
        .all()
    )
    return [
        StatusHistoryResponse(
            id=str(h.id),
            status=h.status,
            changed_at=h.changed_at,
        )
        for h in history
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _order_to_response(order: KitchenOrder) -> KitchenOrderResponse:
    return KitchenOrderResponse(
        id=str(order.id),
        order_id=str(order.order_id),
        status=order.status,
        received_at=order.received_at,
        started_at=order.started_at,
        completed_at=order.completed_at,
        status_history=[
            StatusHistoryResponse(
                id=str(h.id),
                status=h.status,
                changed_at=h.changed_at,
            )
            for h in order.status_history
        ],
    )

