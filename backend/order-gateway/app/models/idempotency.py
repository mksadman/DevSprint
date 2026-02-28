from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IdempotencyStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

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
    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hex digest of the canonical request body",
    )
    response_payload: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Serialised response returned for this order_id",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=IdempotencyStatus.RECEIVED.value,
        comment="Processing state: RECEIVED | CONFIRMED | FAILED",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    def __repr__(self) -> str:
        return (
            f"<IdempotencyKey id={self.id} order_id={self.order_id} "
            f"status={self.status!r}>"
        )
