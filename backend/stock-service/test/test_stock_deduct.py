"""Stock deduction API tests — uses shared conftest fixtures."""
import uuid
from models import Item, Inventory


def test_stock_deduct_flow(client, db_session):
    print("Starting Stock Deduct API Tests...")

    # --- Setup: Create an Item and Inventory ---
    item = Item(name="Stock Item", price=100.0)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    item_id = str(item.id)

    inventory = Inventory(item_id=item.id, quantity=100)
    db_session.add(inventory)
    db_session.commit()

    print(f"Created Item: {item_id} with 100 stock")

    # --- 1. Deduct Stock (Success) ---
    print("\n[TEST 1] Deduct Stock (Success)")
    order_id_1 = str(uuid.uuid4())
    payload = {"order_id": order_id_1, "item_id": item_id, "quantity": 10}
    response = client.post("/stock/deduct", json=payload)
    assert response.status_code == 200, f"FAIL: {response.status_code} - {response.text}"
    data = response.json()
    assert data["status"] == "success"
    print("PASS: Stock deducted")

    # Verify stock via API
    inv_resp = client.get(f"/inventory/{item_id}")
    assert inv_resp.json()["quantity"] == 90
    print("PASS: Stock verified (90)")

    # --- 2. Idempotency Check ---
    print("\n[TEST 2] Idempotency Check")
    response = client.post("/stock/deduct", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Stock already deducted"

    inv_resp = client.get(f"/inventory/{item_id}")
    assert inv_resp.json()["quantity"] == 90
    print("PASS: Idempotency verified (Stock remained 90)")

    # --- 3. Insufficient Stock ---
    print("\n[TEST 3] Insufficient Stock")
    order_id_2 = str(uuid.uuid4())
    response = client.post("/stock/deduct", json={
        "order_id": order_id_2, "item_id": item_id, "quantity": 200
    })
    assert response.status_code == 409
    print("PASS: Insufficient stock handled (409)")

    # --- 4. Invalid Quantity ---
    print("\n[TEST 4] Invalid Quantity")
    order_id_3 = str(uuid.uuid4())
    response = client.post("/stock/deduct", json={
        "order_id": order_id_3, "item_id": item_id, "quantity": -5
    })
    assert response.status_code == 400
    print("PASS: Invalid quantity handled (400)")

    # --- 5. Item Not Found ---
    print("\n[TEST 5] Item Not Found")
    order_id_4 = str(uuid.uuid4())
    response = client.post("/stock/deduct", json={
        "order_id": order_id_4, "item_id": str(uuid.uuid4()), "quantity": 10
    })
    assert response.status_code == 404
    print("PASS: Item not found handled (404)")

    print("\nAll Stock Deduct API tests passed successfully!")
