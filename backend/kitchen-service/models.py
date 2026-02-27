from sqlalchemy import Column, String, DateTime, ForeignKey, create_engine
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
import uuid
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cafeteria:cafeteria_pass@postgres:5432/cafeteria_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class KitchenOrder(Base):
    __tablename__ = 'kitchen_orders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), nullable=False) # Gateway order reference, no FK
    status = Column(String, nullable=False)
    received_at = Column(DateTime, nullable=False, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    status_history = relationship("OrderStatusHistory", back_populates="kitchen_order")

class OrderStatusHistory(Base):
    __tablename__ = 'order_status_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_order_id = Column(UUID(as_uuid=True), ForeignKey('kitchen_orders.id'), nullable=False)
    status = Column(String, nullable=False)
    changed_at = Column(DateTime, nullable=False, default=func.now())

    kitchen_order = relationship("KitchenOrder", back_populates="status_history")
