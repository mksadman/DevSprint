from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, CheckConstraint
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    price = Column(Numeric, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    inventory = relationship("Inventory", uselist=False, back_populates="item")
    stock_transactions = relationship("StockTransaction", back_populates="item")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), unique=True, nullable=False)
    quantity = Column(Integer, CheckConstraint("quantity >= 0"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    item = relationship("Item", back_populates="inventory")
