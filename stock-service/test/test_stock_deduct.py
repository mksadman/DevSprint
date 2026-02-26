import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
import threading
import time

# 1. Setup Environment Variables BEFORE importing app/models
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from models import Base, get_db, Item, Inventory, StockTransaction

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

def test_stock_deduct_flow():
    print("Starting Stock Deduct API Tests...")
    
    # --- Setup: Create an Item and Inventory ---
    db = TestingSessionLocal()
    item = Item(name="Stock Item", price=100.0)
    db.add(item)
    db.commit()
    db.refresh(item)
    item_id = str(item.id)
    
    inventory = Inventory(item_id=item.id, quantity=100)
    db.add(inventory)
    db.commit()
    db.close()
    
    print(f"Created Item: {item_id} with 100 stock")

    # --- 1. Deduct Stock (Success) ---
    print("\n[TEST 1] Deduct Stock (Success)")
    order_id_1 = str(uuid.uuid4())
    payload = {
        "order_id": order_id_1,
        "item_id": item_id,
        "quantity": 10
    }
    response = client.post("/stock/deduct", json=payload)
    if response.status_code != 200:
        print(f"FAIL: {response.status_code} - {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    print("PASS: Stock deducted")
    
    # Verify stock
    db = TestingSessionLocal()
    # Need to query item again or use stored ID string. BUT UUID type expects UUID object, not string.
    inv = db.query(Inventory).filter(Inventory.item_id == uuid.UUID(item_id)).first()
    assert inv.quantity == 90
    db.close()
    print("PASS: Stock verified (90)")

    # --- 2. Idempotency Check ---
    print("\n[TEST 2] Idempotency Check")
    # Send SAME request again
    response = client.post("/stock/deduct", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Stock already deducted"
    
    # Verify stock is STILL 90 (not 80)
    db = TestingSessionLocal()
    inv = db.query(Inventory).filter(Inventory.item_id == uuid.UUID(item_id)).first()
    assert inv.quantity == 90
    db.close()
    print("PASS: Idempotency verified (Stock remained 90)")

    # --- 3. Insufficient Stock ---
    print("\n[TEST 3] Insufficient Stock")
    order_id_2 = str(uuid.uuid4())
    payload_fail = {
        "order_id": order_id_2,
        "item_id": item_id,
        "quantity": 200 # More than 90
    }
    response = client.post("/stock/deduct", json=payload_fail)
    assert response.status_code == 409
    print("PASS: Insufficient stock handled (409)")

    # --- 4. Invalid Quantity ---
    print("\n[TEST 4] Invalid Quantity")
    order_id_3 = str(uuid.uuid4())
    payload_invalid = {
        "order_id": order_id_3,
        "item_id": item_id,
        "quantity": -5
    }
    response = client.post("/stock/deduct", json=payload_invalid)
    assert response.status_code == 400
    print("PASS: Invalid quantity handled (400)")

    # --- 5. Item Not Found ---
    print("\n[TEST 5] Item Not Found")
    order_id_4 = str(uuid.uuid4())
    payload_not_found = {
        "order_id": order_id_4,
        "item_id": str(uuid.uuid4()),
        "quantity": 10
    }
    response = client.post("/stock/deduct", json=payload_not_found)
    assert response.status_code == 404
    print("PASS: Item not found handled (404)")

    print("\nAll Stock Deduct API tests passed successfully!")

if __name__ == "__main__":
    try:
        test_stock_deduct_flow()
    except Exception as e:
        print(f"\nTEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
