"""Transactional outbox — events written here atomically with the order."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    aggregate_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="Order ID that this event belongs to",
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="e.g. order.placed",
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
