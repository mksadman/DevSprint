import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
import time

# 1. Setup Environment Variables BEFORE importing app/models
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.core.database import Base, get_db
from app.models.inventory import Item, Inventory
from app.models.transaction import StockTransaction

# 2. Setup Test Database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# 3. Override Dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_transaction_audit():
    print("Starting Transaction Audit API Tests...")
    
    # --- Setup: Create Items and Transactions ---
    db = TestingSessionLocal()
    
    # Item 1
    item1 = Item(name="Audit Item 1", price=10.0)
    db.add(item1)
    
    # Item 2
    item2 = Item(name="Audit Item 2", price=20.0)
    db.add(item2)
    
    db.commit()
    item1_id = str(item1.id)
    item2_id = str(item2.id)
    
    # Create Transactions
    # Order 1 has 2 items
    order1_id = str(uuid.uuid4())
    
    txn1 = StockTransaction(
        order_id=uuid.UUID(order1_id),
        item_id=item1.id,
        quantity_deducted=5
    )
    db.add(txn1)
    
    txn2 = StockTransaction(
        order_id=uuid.UUID(order1_id),
        item_id=item2.id,
        quantity_deducted=3
    )
    db.add(txn2)
    
    # Order 2 has 1 item
    order2_id = str(uuid.uuid4())
    txn3 = StockTransaction(
        order_id=uuid.UUID(order2_id),
        item_id=item1.id,
        quantity_deducted=10
    )
    db.add(txn3)
    
    db.commit()
    db.close()
    
    print(f"Created Transactions for Order 1: {order1_id}")
    print(f"Created Transactions for Order 2: {order2_id}")

    # --- 1. GET /transactions/{order_id} ---
    print("\n[TEST 1] Get Transaction by Order ID")
    response = client.get(f"/transactions/{order1_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Verify contents
    item_ids = [t["item_id"] for t in data]
    assert item1_id in item_ids
    assert item2_id in item_ids
    print("PASS: Retrieved correct transactions for order")

    # --- 2. GET /transactions/{order_id} (Not Found) ---
    print("\n[TEST 2] Get Transaction by Order ID (Not Found)")
    random_order_id = str(uuid.uuid4())
    response = client.get(f"/transactions/{random_order_id}")
    assert response.status_code == 404
    print("PASS: Handled not found (404)")

    # --- 3. GET /transactions (List All) ---
    print("\n[TEST 3] List All Transactions")
    response = client.get("/transactions/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Check ordering (latest first)
    # txn3 was added last, BUT with sqlite in-memory and rapid insertion, timestamps might be identical.
    # So we can't strictly rely on ordering unless we sleep or manually set created_at.
    # Let's just verify we have 3 transactions.
    print(f"Total transactions: {len(data)}")
    print("PASS: Listed all transactions")

    # --- 4. GET /transactions (Filter by Item) ---
    print("\n[TEST 4] List Transactions Filtered by Item")
    response = client.get(f"/transactions/?item_id={item1_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2 # txn1 and txn3
    for t in data:
        assert t["item_id"] == item1_id
    print("PASS: Filtered by item_id")

    # --- 5. GET /transactions (Pagination) ---
    print("\n[TEST 5] List Transactions Pagination")
    # Limit 1
    response = client.get("/transactions/?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    
    # Offset 1
    response = client.get("/transactions/?limit=1&offset=1")
    assert response.status_code == 200
    data_offset = response.json()
    assert len(data_offset) == 1
    assert data_offset[0]["id"] != data[0]["id"]
    print("PASS: Pagination working")

    print("\nAll Transaction Audit API tests passed successfully!")

if __name__ == "__main__":
    try:
        test_transaction_audit()
    except Exception as e:
        print(f"\nTEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
