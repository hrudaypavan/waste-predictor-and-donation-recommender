from fastapi import FastAPI, Depends, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from datetime import date, datetime
import joblib
import os

from . import models, database, crud

# Initialize FastAPI
app = FastAPI(title="Grocery Waste Predictor API")

# Enable CORS so frontend JS can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

@app.on_event("startup")
def startup_event():
    try:
        with database.engine.begin() as conn:
            conn.execute(text("ALTER TABLE groceries ADD COLUMN category VARCHAR DEFAULT 'General'"))
    except Exception:
        pass

# Dependency: DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Load Machine Learning Model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "grocery_model.joblib")
ml_model = None
if os.path.exists(MODEL_PATH):
    try:
        ml_model = joblib.load(MODEL_PATH)
        print("Machine learning model loaded successfully!")
    except Exception as e:
        print(f"Error loading machine learning model: {e}")
else:
    print(f"Warning: ML model file not found at {MODEL_PATH}. Standalone training needed.")

# Category mapping helper for ML prediction
CATEGORIES = {
    'Dairy': {'perishability': 3, 'temp': 4},
    'Fruits': {'perishability': 2, 'temp': 25},
    'Vegetables': {'perishability': 2, 'temp': 25},
    'Meat/Fish': {'perishability': 3, 'temp': 4},
    'Bakery': {'perishability': 3, 'temp': 25},
    'Pantry/Grains': {'perishability': 1, 'temp': 25},
    'Frozen Foods': {'perishability': 1, 'temp': -18}
}

def predict_item_waste(quantity: float, p_date: str, e_date: str, category: str):
    # Calculate days to expiry
    try:
        d1 = date.fromisoformat(p_date)
        d2 = date.fromisoformat(e_date)
        days_left = (d2 - d1).days
        if days_left < 1:
            days_left = 1
    except:
        days_left = 7
        
    info = CATEGORIES.get(category, {'perishability': 2, 'temp': 25})
    temp = info['temp']
    perishability = info['perishability']
    
    if ml_model:
        try:
            # Features: quantity, days_to_expiry, storage_temperature, perishability_index
            prediction = ml_model.predict([[quantity, days_left, temp, perishability]])[0]
            prediction = float(round(prediction, 2))
        except Exception as e:
            print(f"Inference error: {e}")
            prediction = 50.0 # fallback
    else:
        # Rule-based fallback
        base_waste = (perishability * 15) + (30 - days_left) * 1.5 + (temp * 0.8) + (quantity * 1.2)
        prediction = min(max(base_waste, 0.0), 100.0)
        
    # Classify risk level
    if prediction < 30.0:
        risk_level = "Low"
    elif prediction < 75.0:
        risk_level = "Medium"
    else:
        risk_level = "High"
        
    return prediction, risk_level

# --- SCHEMAS ---

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ItemCreate(BaseModel):
    item_name: str
    category: str
    quantity: float
    purchase_date: str
    expiration_date: str
    user_id: int

class ItemUpdate(BaseModel):
    item_name: str
    category: str
    quantity: float
    purchase_date: str
    expiration_date: str

class StatusUpdate(BaseModel):
    status: str

# --- API ROUTES ---

@app.post("/api/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_email = crud.get_user_by_email(db, user.email)
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = crud.create_user(db, user.dict())
    return {"message": "User registered successfully", "user_id": new_user.id}

@app.post("/api/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, user.username)
    if not db_user or not crud.verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
        
    return {
        "message": "Login successful",
        "user_id": db_user.id,
        "username": db_user.username,
        "email": db_user.email
    }

@app.post("/api/groceries")
def add_item(item: ItemCreate, db: Session = Depends(get_db)):
    # Run waste ML prediction
    predicted_waste, risk_level = predict_item_waste(
        item.quantity, item.purchase_date, item.expiration_date, item.category
    )
    
    item_data = item.dict()
    db_item = crud.add_grocery_item(db, item_data, item.user_id, predicted_waste, risk_level)
    return db_item

@app.get("/api/groceries")
def list_items(user_id: int, search: str = None, db: Session = Depends(get_db)):
    return crud.get_grocery_items(db, user_id=user_id, search=search)

@app.put("/api/groceries/{id}")
def update_item(id: int, item: ItemUpdate, db: Session = Depends(get_db)):
    predicted_waste, risk_level = predict_item_waste(
        item.quantity, item.purchase_date, item.expiration_date, item.category
    )
    db_item = crud.update_grocery_item(db, id, item.dict(), predicted_waste, risk_level)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@app.delete("/api/groceries/{id}")
def delete_item(id: int, db: Session = Depends(get_db)):
    success = crud.delete_grocery_item(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}

@app.patch("/api/groceries/{id}/status")
def update_status(id: int, status_update: StatusUpdate, db: Session = Depends(get_db)):
    db_item = crud.update_item_status(db, id, status_update.status)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@app.get("/api/groceries/stats")
def get_stats(user_id: int, db: Session = Depends(get_db)):
    return crud.get_dashboard_stats(db, user_id=user_id)

# --- RECIPE RECOMMENDATIONS ENGINE ---

RECIPES = {
    "Dairy": [
        {"title": "Homemade Paneer", "ingredients": "Milk, Lemon juice", "steps": "Boil milk, add lemon juice to curdle, strain and press into a block."},
        {"title": "Fruit Custard", "ingredients": "Milk, Sugar, Custard powder, Mixed fruits", "steps": "Mix custard powder in cold milk. Boil milk and sugar, slowly stir in custard paste, cool, and add fruits."},
        {"title": "Cheese Melt Sandwich", "ingredients": "Cheese slice, Bread, Butter", "steps": "Butter bread, place cheese inside, grill on pan until golden brown and cheese melts."}
    ],
    "Fruits": [
        {"title": "Fresh Fruit Salad", "ingredients": "Apples, Bananas, Oranges, Honey", "steps": "Chop fruits, toss in honey and lemon juice, chill and serve."},
        {"title": "Banana Bread", "ingredients": "Overripe Bananas, Flour, Sugar, Butter, Baking Soda", "steps": "Mash bananas, mix with wet and dry ingredients, bake at 180°C for 45 minutes."}
    ],
    "Vegetables": [
        {"title": "Tomato Pasta Sauce", "ingredients": "Tomatoes, Garlic, Olive oil, Basil, Salt", "steps": "Blanch and blend tomatoes, sauté garlic in olive oil, simmer tomatoes with herbs until thick."},
        {"title": "Spinach Garlic Sauté", "ingredients": "Spinach, Garlic, Olive oil, Salt, Red pepper flakes", "steps": "Sauté minced garlic in olive oil, add spinach, cook until wilted, season with salt."}
    ],
    "Meat/Fish": [
        {"title": "Grilled Herb Chicken", "ingredients": "Chicken breast, Garlic, Rosemary, Olive oil, Lemon juice", "steps": "Marinate chicken in herbs, garlic, oil, and lemon. Grill on a hot pan until cooked through."},
        {"title": "Pan-seared Salmon", "ingredients": "Salmon fillet, Garlic butter, Lemon, Dill", "steps": "Sear salmon skin-side down for 4 mins, flip, baste with garlic butter and lemon juice."}
    ],
    "Bakery": [
        {"title": "Garlic Croutons", "ingredients": "Stale Bread, Olive oil, Garlic powder, Herbs", "steps": "Cube bread, toss in olive oil and seasonings, bake or pan-fry until crunchy."}
    ],
    "Pantry/Grains": [
        {"title": "Vegetable Fried Rice", "ingredients": "Rice, Mixed veggies, Soy sauce, Garlic", "steps": "Stir-fry garlic and veggies in oil, toss with cold cooked rice and soy sauce on high heat."},
        {"title": "Sweet Rice Kheer", "ingredients": "Rice, Milk, Sugar, Cardamom, Nuts", "steps": "Boil rice in milk on low heat until soft and thick, stir in sugar, cardamom, and top with nuts."}
    ]
}

@app.get("/api/recipes/recommend")
def recommend_recipes(user_id: int, db: Session = Depends(get_db)):
    # Find items expiring in next 5 days
    items = db.query(models.GroceryItem).filter(
        models.GroceryItem.user_id == user_id,
        models.GroceryItem.status == "remaining"
    ).all()
    
    today = date.today()
    expiring_categories = set()
    expiring_items = []
    
    for item in items:
        days_left = (item.expiration_date - today).days
        if 0 <= days_left <= 5:
            # Map item names to categorizations if category field is somehow blank
            category = "Pantry/Grains"
            for cat, data in CATEGORIES.items():
                # Basic name matching
                if item.item_name.lower() in ["milk", "cheese", "yogurt", "paneer"]:
                    category = "Dairy"
                elif item.item_name.lower() in ["apple", "banana", "orange", "grape"]:
                    category = "Fruits"
                elif item.item_name.lower() in ["tomato", "spinach", "potato", "onion"]:
                    category = "Vegetables"
                elif item.item_name.lower() in ["chicken", "fish", "salmon", "meat"]:
                    category = "Meat/Fish"
                elif item.item_name.lower() in ["bread", "bun", "cake"]:
                    category = "Bakery"
            
            expiring_categories.add(category)
            expiring_items.append({"name": item.item_name, "days_left": days_left})
            
    recommendations = []
    for cat in expiring_categories:
        if cat in RECIPES:
            for recipe in RECIPES[cat]:
                recommendations.append({
                    "recipe_title": recipe["title"],
                    "matched_ingredient": cat,
                    "ingredients": recipe["ingredients"],
                    "steps": recipe["steps"]
                })
                
    # If no items are expiring soon, return standard recommendations
    if not recommendations:
        for cat in ["Pantry/Grains", "Dairy", "Vegetables"]:
            recipe = RECIPES[cat][0]
            recommendations.append({
                "recipe_title": recipe["title"],
                "matched_ingredient": "General Pantry",
                "ingredients": recipe["ingredients"],
                "steps": recipe["steps"]
            })
            
    return {"expiring_items": expiring_items, "recipes": recommendations[:4]}