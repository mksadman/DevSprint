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

from main import app
from models import Base, get_db, Item, Inventory

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

def test_admin_endpoints():
    print("Starting Admin API Tests (Health & Metrics)...")
    
    # --- 1. GET /health (Success) ---
    print("\n[TEST 1] Health Check - Success")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    print("PASS: Health check OK")

    # --- 2. GET /metrics (Initial) ---
    print("\n[TEST 2] Metrics Check (Initial)")
    # The health check above should have incremented total_requests
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    
    text = response.text
    print(f"Metrics Output:\n{text}")
    
    # Verify format
    assert "total_requests" in text
    assert "total_deductions" in text
    assert "average_latency_ms" in text
    
    # Parse metrics
    metrics = {}
    for line in text.splitlines():
        if " " in line:
            parts = line.split(" ", 1)
            # handle request_count{...} key
            metrics[parts[0]] = parts[1]
            
    assert int(metrics["total_requests"]) >= 1
    print("PASS: Metrics format and basic counters OK")

    # --- 3. Test Deductions Metrics ---
    print("\n[TEST 3] Deduction Metrics")
    
    # Create Item and Inventory
    db = TestingSessionLocal()
    item = Item(name="Metric Item", price=10.0)
    db.add(item)
    db.commit()
    item_id = str(item.id)
    inv = Inventory(item_id=item.id, quantity=100)
    db.add(inv)
    db.commit()
    db.close()
    
    # Successful Deduction
    client.post("/stock/deduct", json={
        "order_id": str(uuid.uuid4()),
        "item_id": item_id,
        "quantity": 10
    })
    
    # Failed Deduction (Insufficient stock)
    client.post("/stock/deduct", json={
        "order_id": str(uuid.uuid4()),
        "item_id": item_id,
        "quantity": 200
    })
    
    # Check metrics again
    response = client.get("/metrics")
    text = response.text
    metrics = {}
    for line in text.splitlines():
        if " " in line:
            parts = line.split(" ", 1)
            metrics[parts[0]] = parts[1]
            
    print(f"Updated Metrics:\n{text}")
    
    assert int(metrics["total_deductions"]) == 2 # 1 success + 1 fail
    assert int(metrics["failed_deductions"]) == 1
    print("PASS: Deduction metrics tracked correctly")

    print("\nAll Admin API tests passed successfully!")

if __name__ == "__main__":
    try:
        test_admin_endpoints()
    except Exception as e:
        print(f"\nTEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
