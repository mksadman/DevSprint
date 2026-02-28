"""Item catalog CRUD tests — uses TestClient (no live server needed)."""
import uuid
from models import Item


def test_crud(client, db_session):
    print("Testing CRUD endpoints...")

    # 1. Create Item
    print("\n1. Create Item")
    item_data = {"name": "Test Item", "price": 10.50}
    response = client.post("/items", json=item_data)
    assert response.status_code == 201
    item = response.json()
    print(f"Created: {item}")
    item_id = item["id"]

    # 2. Get All Items
    print("\n2. Get All Items")
    response = client.get("/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    print(f"Found {len(items)} items")

    # 3. Get Single Item
    print(f"\n3. Get Single Item {item_id}")
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    print(f"Got item: {response.json()}")

    # 4. Update Item (PUT)
    print(f"\n4. Update Item (PUT) {item_id}")
    update_data = {"name": "Updated Item", "price": 15.00}
    response = client.put(f"/items/{item_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Item"
    print(f"Updated: {response.json()}")

    # 5. Partial Update (PATCH)
    print(f"\n5. Partial Update (PATCH) {item_id}")
    patch_data = {"price": 20.00}
    response = client.patch(f"/items/{item_id}", json=patch_data)
    assert response.status_code == 200
    assert float(response.json()["price"]) == 20.00
    print(f"Patched: {response.json()}")

    # 6. Delete Item
    print(f"\n6. Delete Item {item_id}")
    response = client.delete(f"/items/{item_id}")
    assert response.status_code == 204
    print("Deleted successfully")

    # 7. Verify Delete
    print(f"\n7. Verify Delete {item_id}")
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 404
    print("Item not found (as expected)")

    print("\nAll CRUD tests passed!")
