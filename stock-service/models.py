from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, CheckConstraint, create_engine
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

class Item(Base):
    __tablename__ = 'items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    price = Column(Numeric, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    inventory = relationship("Inventory", uselist=False, back_populates="item")
    stock_transactions = relationship("StockTransaction", back_populates="item")

class Inventory(Base):
    __tablename__ = 'inventory'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey('items.id'), unique=True, nullable=False)
    quantity = Column(Integer, CheckConstraint('quantity >= 0'), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    item = relationship("Item", back_populates="inventory")

class StockTransaction(Base):
    __tablename__ = 'stock_transactions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), nullable=False) # Logical reference, no FK
    item_id = Column(UUID(as_uuid=True), ForeignKey('items.id'), nullable=False)
    quantity_deducted = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    item = relationship("Item", back_populates="stock_transactions")
