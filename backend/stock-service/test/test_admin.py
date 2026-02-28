"""Admin endpoint tests (health & metrics) — uses shared conftest fixtures."""
import uuid
from models import Item, Inventory


def test_admin_endpoints(client, db_session):
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
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    text = response.text
    print(f"Metrics Output:\n{text}")

    assert "total_requests" in text
    assert "total_deductions" in text
    assert "average_latency_ms" in text

    metrics = {}
    for line in text.splitlines():
        if " " in line:
            parts = line.split(" ", 1)
            metrics[parts[0]] = parts[1]

    assert int(metrics["total_requests"]) >= 1
    print("PASS: Metrics format and basic counters OK")

    # --- 3. Test Deductions Metrics ---
    print("\n[TEST 3] Deduction Metrics")

    item = Item(name="Metric Item", price=10.0)
    db_session.add(item)
    db_session.commit()
    item_id = str(item.id)
    inv = Inventory(item_id=item.id, quantity=100)
    db_session.add(inv)
    db_session.commit()

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

    assert int(metrics["total_deductions"]) == 2  # 1 success + 1 fail
    assert int(metrics["failed_deductions"]) == 1
    print("PASS: Deduction metrics tracked correctly")

    print("\nAll Admin API tests passed successfully!")
