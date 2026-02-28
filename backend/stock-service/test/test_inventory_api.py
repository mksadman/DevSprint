import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid

# 1. Setup Environment Variables BEFORE importing app/models
# This ensures models.py uses the SQLite DB or we can override it later.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.core.database import Base, get_db
from app.models.inventory import Item, Inventory
from app.models.transaction import StockTransaction

# 2. Setup Test Database
# We use Shared In-Memory SQLite with StaticPool so multiple threads (if any) share the same DB
# and it persists across connections until the process ends.
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

def test_inventory_api_flow():
    print("Starting Inventory API Tests...")
    
    # --- Setup: Create an Item ---
    db = TestingSessionLocal()
    # Create Item 1 (for normal flow)
    item1 = Item(name="Test Item 1", price=10.5)
    db.add(item1)
    
    # Create Item 2 (for transaction constraint test)
    item2 = Item(name="Test Item 2", price=20.0)
    db.add(item2)
    
    db.commit()
    db.refresh(item1)
    db.refresh(item2)
    item_id_1 = str(item1.id)
    item_id_2 = str(item2.id)
    
    # Create Transaction for Item 2
    txn = StockTransaction(
        order_id=uuid.uuid4(),
        item_id=item2.id,
        quantity_deducted=5
    )
    db.add(txn)
    
    # Also create Inventory for Item 2 so we can try to delete it
    inv2 = Inventory(item_id=item2.id, quantity=50)
    db.add(inv2)
    
    db.commit()
    db.close()
    
    print(f"Created Item 1: {item_id_1}")
    print(f"Created Item 2 (with transactions): {item_id_2}")

    # --- 1. POST /inventory (Success) ---
    print("\n[TEST 1] Create Inventory (POST) - Success")
    response = client.post(
        "/inventory/",
        json={"item_id": item_id_1, "quantity": 100}
    )
    if response.status_code != 201:
        print(f"FAIL: {response.status_code} - {response.text}")
    assert response.status_code == 201
    data = response.json()
    assert data["item_id"] == item_id_1
    assert data["quantity"] == 100
    assert data["version"] == 1
    print("PASS: Created inventory")

    # --- 2. POST /inventory (Conflict) ---
    print("\n[TEST 2] Create Duplicate Inventory (POST) - Conflict")
    response = client.post(
        "/inventory/",
        json={"item_id": item_id_1, "quantity": 50}
    )
    assert response.status_code == 409
    print("PASS: Detected conflict (409)")

    # --- 3. GET /inventory/{item_id} ---
    print("\n[TEST 3] Get Inventory (GET) - Success")
    response = client.get(f"/inventory/{item_id_1}")
    assert response.status_code == 200
    assert response.json()["quantity"] == 100
    print("PASS: Retrieved inventory")

    # --- 4. PUT /inventory/{item_id} ---
    print("\n[TEST 4] Update Inventory (PUT) - Success")
    response = client.put(
        f"/inventory/{item_id_1}",
        json={"quantity": 200}
    )
    assert response.status_code == 200
    assert response.json()["quantity"] == 200
    assert response.json()["version"] == 2
    print("PASS: Updated inventory via PUT")

    # --- 5. PATCH /inventory/{item_id} (Positive) ---
    print("\n[TEST 5] Adjust Inventory Positive (PATCH) - Success")
    response = client.patch(
        f"/inventory/{item_id_1}",
        json={"delta": 50}
    )
    assert response.status_code == 200
    assert response.json()["quantity"] == 250
    assert response.json()["version"] == 3
    print("PASS: Adjusted inventory (+50)")

    # --- 6. PATCH /inventory/{item_id} (Negative) ---
    print("\n[TEST 6] Adjust Inventory Negative (PATCH) - Success")
    response = client.patch(
        f"/inventory/{item_id_1}",
        json={"delta": -50}
    )
    assert response.status_code == 200
    assert response.json()["quantity"] == 200
    assert response.json()["version"] == 4
    print("PASS: Adjusted inventory (-50)")

    # --- 7. PATCH /inventory/{item_id} (Fail < 0) ---
    print("\n[TEST 7] Adjust Inventory Below Zero (PATCH) - Fail")
    response = client.patch(
        f"/inventory/{item_id_1}",
        json={"delta": -300}
    )
    assert response.status_code == 400
    # Check DB state didn't change
    response = client.get(f"/inventory/{item_id_1}")
    assert response.json()["quantity"] == 200
    print("PASS: Prevented negative stock (400)")

    # --- 8. DELETE /inventory/{item_id} (With Transactions) ---
    print("\n[TEST 8] Delete Inventory with Transactions (DELETE) - Conflict")
    response = client.delete(f"/inventory/{item_id_2}")
    assert response.status_code == 409
    print("PASS: Prevented delete due to existing transactions (409)")

    # --- 9. DELETE /inventory/{item_id} (Success) ---
    print("\n[TEST 9] Delete Inventory (DELETE) - Success")
    response = client.delete(f"/inventory/{item_id_1}")
    assert response.status_code == 204
    
    # Verify it's gone
    response = client.get(f"/inventory/{item_id_1}")
    assert response.status_code == 404
    print("PASS: Deleted inventory (204 -> 404)")

    print("\nAll Inventory API tests passed successfully!")

if __name__ == "__main__":
    try:
        test_inventory_api_flow()
    except Exception as e:
        print(f"\nTEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
