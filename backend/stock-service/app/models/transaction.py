from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    quantity_deducted = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    item = relationship("Item", back_populates="stock_transactions")
