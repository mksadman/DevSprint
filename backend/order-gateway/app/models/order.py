from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GatewayOrder(Base):
    __tablename__ = "gateway_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
    )
    student_id: Mapped[str] = mapped_column(String(128), nullable=False)
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=OrderStatus.RECEIVED.value,
        comment="Order state: RECEIVED | CONFIRMED | REJECTED",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )

    def __repr__(self) -> str:
        return (
            f"<GatewayOrder id={self.id} order_id={self.order_id} "
            f"item_id={self.item_id!r} quantity={self.quantity} "
            f"status={self.status!r}>"
        )
