"""Inventory API tests — uses shared conftest fixtures."""
import uuid
from models import Item, Inventory, StockTransaction


def test_inventory_api_flow(client, db_session):
    print("Starting Inventory API Tests...")

    # --- Setup: Create Items ---
    item1 = Item(name="Test Item 1", price=10.5)
    db_session.add(item1)
    item2 = Item(name="Test Item 2", price=20.0)
    db_session.add(item2)
    db_session.commit()
    db_session.refresh(item1)
    db_session.refresh(item2)
    item_id_1 = str(item1.id)
    item_id_2 = str(item2.id)

    # Transaction for Item 2 (prevents deletion)
    txn = StockTransaction(order_id=uuid.uuid4(), item_id=item2.id, quantity_deducted=5)
    db_session.add(txn)
    inv2 = Inventory(item_id=item2.id, quantity=50)
    db_session.add(inv2)
    db_session.commit()

    print(f"Created Item 1: {item_id_1}")
    print(f"Created Item 2 (with transactions): {item_id_2}")

    # --- 1. POST /inventory (Success) ---
    print("\n[TEST 1] Create Inventory (POST) - Success")
    response = client.post("/inventory/", json={"item_id": item_id_1, "quantity": 100})
    assert response.status_code == 201, f"FAIL: {response.status_code} - {response.text}"
    data = response.json()
    assert data["item_id"] == item_id_1
    assert data["quantity"] == 100
    assert data["version"] == 1
    print("PASS: Created inventory")

    # --- 2. POST /inventory (Conflict) ---
    print("\n[TEST 2] Create Duplicate Inventory (POST) - Conflict")
    response = client.post("/inventory/", json={"item_id": item_id_1, "quantity": 50})
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
    response = client.put(f"/inventory/{item_id_1}", json={"quantity": 200})
    assert response.status_code == 200
    assert response.json()["quantity"] == 200
    assert response.json()["version"] == 2
    print("PASS: Updated inventory via PUT")

    # --- 5. PATCH /inventory/{item_id} (Positive) ---
    print("\n[TEST 5] Adjust Inventory Positive (PATCH) - Success")
    response = client.patch(f"/inventory/{item_id_1}", json={"delta": 50})
    assert response.status_code == 200
    assert response.json()["quantity"] == 250
    assert response.json()["version"] == 3
    print("PASS: Adjusted inventory (+50)")

    # --- 6. PATCH /inventory/{item_id} (Negative) ---
    print("\n[TEST 6] Adjust Inventory Negative (PATCH) - Success")
    response = client.patch(f"/inventory/{item_id_1}", json={"delta": -50})
    assert response.status_code == 200
    assert response.json()["quantity"] == 200
    assert response.json()["version"] == 4
    print("PASS: Adjusted inventory (-50)")

    # --- 7. PATCH /inventory/{item_id} (Fail < 0) ---
    print("\n[TEST 7] Adjust Inventory Below Zero (PATCH) - Fail")
    response = client.patch(f"/inventory/{item_id_1}", json={"delta": -300})
    assert response.status_code == 400
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
    response = client.get(f"/inventory/{item_id_1}")
    assert response.status_code == 404
    print("PASS: Deleted inventory (204 -> 404)")

    print("\nAll Inventory API tests passed successfully!")
