from fastapi.testclient import TestClient
import sys
import os

# Adjust path to find the backend module
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from backend.main import app
    print("Successfully imported FastAPI app!")
except Exception as e:
    print(f"Error importing FastAPI app: {e}")
    sys.exit(1)

client = TestClient(app)

def test_workflow():
    print("\n--- Starting Backend Test Workflow ---")
    
    # 1. Test registration
    username = f"testuser_{os.urandom(3).hex()}"
    email = f"{username}@test.com"
    reg_data = {
        "username": username,
        "email": email,
        "password": "testpassword123"
    }
    
    print(f"Testing Registration for user: {username}...")
    res = client.post("/api/register", json=reg_data)
    assert res.status_code == 200, f"Registration failed: {res.text}"
    user_id = res.json()["user_id"]
    print(f"SUCCESS: Registration successful! User ID: {user_id}")
    
    # 2. Test login
    print("Testing Login...")
    login_data = {
        "username": username,
        "password": "testpassword123"
    }
    res = client.post("/api/login", json=login_data)
    assert res.status_code == 200, f"Login failed: {res.text}"
    print(f"SUCCESS: Login successful! Response: {res.json()}")
    
    # 3. Test add item (which triggers ML waste risk prediction)
    print("Testing Add Grocery Item (Triggers ML Prediction)...")
    item_data = {
        "item_name": "Milk",
        "category": "Dairy",
        "quantity": 2.5,
        "purchase_date": "2026-06-29",
        "expiration_date": "2026-07-02", # 3 days left
        "user_id": user_id
    }
    res = client.post("/api/groceries", json=item_data)
    assert res.status_code == 200, f"Add item failed: {res.text}"
    item = res.json()
    item_id = item["id"]
    print(f"SUCCESS: Grocery item added successfully!")
    print(f"  Item ID: {item_id}")
    print(f"  Predicted Waste: {item['predicted_waste_percent']}%")
    print(f"  Waste Risk Level: {item['waste_risk_level']}")
    
    # 4. Test list items
    print("Testing List Grocery Items...")
    res = client.get(f"/api/groceries?user_id={user_id}")
    assert res.status_code == 200, f"List items failed: {res.text}"
    items = res.json()
    assert len(items) == 1, "Expected 1 item in list"
    print(f"SUCCESS: Listed items successfully! Found: {items[0]['item_name']}")
    
    # 5. Test search filter
    print("Testing List Grocery Items with search query...")
    res = client.get(f"/api/groceries?user_id={user_id}&search=Mil")
    assert res.status_code == 200, "Search query failed"
    assert len(res.json()) == 1, "Expected 1 item matching 'Mil'"
    
    res = client.get(f"/api/groceries?user_id={user_id}&search=Apple")
    assert len(res.json()) == 0, "Expected 0 items matching 'Apple'"
    print("SUCCESS: Search filter successfully verified!")
    
    # 6. Test edit item details
    print("Testing Edit Item Details...")
    edit_data = {
        "item_name": "Organic Milk",
        "category": "Dairy",
        "quantity": 3.0,
        "purchase_date": "2026-06-29",
        "expiration_date": "2026-07-05" # 6 days left (different prediction)
    }
    res = client.put(f"/api/groceries/{item_id}", json=edit_data)
    assert res.status_code == 200, f"Edit item failed: {res.text}"
    edited_item = res.json()
    print(f"SUCCESS: Edit item successful! New Name: {edited_item['item_name']}, Qty: {edited_item['quantity']}")
    print(f"  New Predicted Waste: {edited_item['predicted_waste_percent']}%")
    
    # 7. Test update status to donated
    print("Testing Mark as Donated...")
    res = client.patch(f"/api/groceries/{item_id}/status", json={"status": "donated"})
    assert res.status_code == 200, f"Mark donated failed: {res.text}"
    donated_item = res.json()
    assert donated_item["status"] == "donated", "Expected status to be 'donated'"
    print("SUCCESS: Mark as Donated successful!")
    
    # 8. Test get dashboard stats
    print("Testing Dashboard Statistics...")
    res = client.get(f"/api/groceries/stats?user_id={user_id}")
    assert res.status_code == 200, f"Stats failed: {res.text}"
    stats = res.json()
    print(f"SUCCESS: Stats successful! Details: {stats}")
    assert stats["donated_count"] == 1
    
    # 9. Test recipe recommendation
    print("Testing Recipe Recommendations...")
    res = client.get(f"/api/recipes/recommend?user_id={user_id}")
    assert res.status_code == 200, f"Recipe recommendation failed: {res.text}"
    recipes = res.json()["recipes"]
    print(f"SUCCESS: Recipe recommendation successful! Recommended recipes: {[r['recipe_title'] for r in recipes]}")
    
    # 10. Test delete item
    print("Testing Delete Item...")
    res = client.delete(f"/api/groceries/{item_id}")
    assert res.status_code == 200, f"Delete failed: {res.text}"
    
    # Verify deletion
    res = client.get(f"/api/groceries?user_id={user_id}")
    assert len(res.json()) == 0, "Item should have been deleted"
    print("SUCCESS: Delete successful!")
    
    print("\n--- All Backend Tests Passed Successfully! ---")

if __name__ == "__main__":
    test_workflow()
