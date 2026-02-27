from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class Order(Base):
    __tablename__ = 'orders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationship to IdempotencyKey
    idempotency_key = relationship("IdempotencyKey", uselist=False, back_populates="order")

class IdempotencyKey(Base):
    __tablename__ = 'idempotency_keys'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False)
    key = Column(String, unique=True, nullable=False)
    response_snapshot = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    order = relationship("Order", back_populates="idempotency_key")
