"""Transaction audit API tests — uses shared conftest fixtures."""
import uuid
from models import Item, StockTransaction


def test_transaction_audit(client, db_session):
    print("Starting Transaction Audit API Tests...")

    # --- Setup: Create Items and Transactions ---
    item1 = Item(name="Audit Item 1", price=10.0)
    db_session.add(item1)
    item2 = Item(name="Audit Item 2", price=20.0)
    db_session.add(item2)
    db_session.commit()
    item1_id = str(item1.id)
    item2_id = str(item2.id)

    order1_id = str(uuid.uuid4())
    txn1 = StockTransaction(
        order_id=uuid.UUID(order1_id),
        item_id=item1.id,
        quantity_deducted=5,
    )
    db_session.add(txn1)

    txn2 = StockTransaction(
        order_id=uuid.UUID(order1_id),
        item_id=item2.id,
        quantity_deducted=3,
    )
    db_session.add(txn2)

    order2_id = str(uuid.uuid4())
    txn3 = StockTransaction(
        order_id=uuid.UUID(order2_id),
        item_id=item1.id,
        quantity_deducted=10,
    )
    db_session.add(txn3)
    db_session.commit()

    print(f"Created Transactions for Order 1: {order1_id}")
    print(f"Created Transactions for Order 2: {order2_id}")

    # --- 1. GET /transactions/{order_id} ---
    print("\n[TEST 1] Get Transaction by Order ID")
    response = client.get(f"/transactions/{order1_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
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
    print(f"Total transactions: {len(data)}")
    print("PASS: Listed all transactions")

    # --- 4. GET /transactions (Filter by Item) ---
    print("\n[TEST 4] List Transactions Filtered by Item")
    response = client.get(f"/transactions/?item_id={item1_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # txn1 and txn3
    for t in data:
        assert t["item_id"] == item1_id
    print("PASS: Filtered by item_id")

    # --- 5. GET /transactions (Pagination) ---
    print("\n[TEST 5] List Transactions Pagination")
    response = client.get("/transactions/?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    response = client.get("/transactions/?limit=1&offset=1")
    assert response.status_code == 200
    data_offset = response.json()
    assert len(data_offset) == 1
    assert data_offset[0]["id"] != data[0]["id"]
    print("PASS: Pagination working")

    print("\nAll Transaction Audit API tests passed successfully!")
