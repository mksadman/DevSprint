from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class KitchenOrder(Base):
    __tablename__ = "kitchen_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False)
    received_at = Column(DateTime, nullable=False, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    status_history = relationship("OrderStatusHistory", back_populates="kitchen_order")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_order_id = Column(
        UUID(as_uuid=True), ForeignKey("kitchen_orders.id"), nullable=False
    )
    status = Column(String, nullable=False)
    changed_at = Column(DateTime, nullable=False, default=func.now())

    kitchen_order = relationship("KitchenOrder", back_populates="status_history")
