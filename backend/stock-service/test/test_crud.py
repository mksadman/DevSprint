import requests
import uuid

BASE_URL = "http://localhost:8002"

def test_crud():
    print("Testing CRUD endpoints...")

    # 1. Create Item
    print("\n1. Create Item")
    item_data = {"name": "Test Item", "price": 10.50}
    response = requests.post(f"{BASE_URL}/items", json=item_data)
    if response.status_code == 201:
        item = response.json()
        print(f"Created: {item}")
        item_id = item['id']
    else:
        print(f"Failed to create: {response.status_code} {response.text}")
        return

    # 2. Get All Items
    print("\n2. Get All Items")
    response = requests.get(f"{BASE_URL}/items")
    if response.status_code == 200:
        items = response.json()
        print(f"Found {len(items)} items")
    else:
        print(f"Failed to get items: {response.status_code} {response.text}")

    # 3. Get Single Item
    print(f"\n3. Get Single Item {item_id}")
    response = requests.get(f"{BASE_URL}/items/{item_id}")
    if response.status_code == 200:
        print(f"Got item: {response.json()}")
    else:
        print(f"Failed to get item: {response.status_code} {response.text}")

    # 4. Update Item (PUT)
    print(f"\n4. Update Item (PUT) {item_id}")
    update_data = {"name": "Updated Item", "price": 15.00}
    response = requests.put(f"{BASE_URL}/items/{item_id}", json=update_data)
    if response.status_code == 200:
        print(f"Updated: {response.json()}")
    else:
        print(f"Failed to update: {response.status_code} {response.text}")

    # 5. Partial Update (PATCH)
    print(f"\n5. Partial Update (PATCH) {item_id}")
    patch_data = {"price": 20.00}
    response = requests.patch(f"{BASE_URL}/items/{item_id}", json=patch_data)
    if response.status_code == 200:
        print(f"Patched: {response.json()}")
    else:
        print(f"Failed to patch: {response.status_code} {response.text}")

    # 6. Delete Item
    print(f"\n6. Delete Item {item_id}")
    response = requests.delete(f"{BASE_URL}/items/{item_id}")
    if response.status_code == 204:
        print("Deleted successfully")
    else:
        print(f"Failed to delete: {response.status_code} {response.text}")

    # 7. Verify Delete
    print(f"\n7. Verify Delete {item_id}")
    response = requests.get(f"{BASE_URL}/items/{item_id}")
    if response.status_code == 404:
        print("Item not found (as expected)")
    else:
        print(f"Item still exists or error: {response.status_code}")

if __name__ == "__main__":
    test_crud()
