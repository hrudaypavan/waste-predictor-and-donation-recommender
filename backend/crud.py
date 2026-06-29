from sqlalchemy.orm import Session
from .models import User, GroceryItem
from datetime import date, datetime, timedelta
import bcrypt

# --- USER CRUD ---

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data: dict):
    # Hash password using bcrypt
    salt = bcrypt.gensalt()
    hashed_pwd = bcrypt.hashpw(user_data["password"].encode('utf-8'), salt).decode('utf-8')
    
    new_user = User(
        username=user_data["username"],
        email=user_data["email"],
        password_hash=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# --- GROCERY ITEM CRUD ---

def add_grocery_item(db: Session, item_data: dict, user_id: int, predicted_waste: float, risk_level: str):
    new_item = GroceryItem(
        user_id=user_id,
        item_name=item_data["item_name"],
        quantity=item_data["quantity"],
        purchase_date=date.fromisoformat(item_data["purchase_date"]),
        expiration_date=date.fromisoformat(item_data["expiration_date"]),
        predicted_waste_percent=predicted_waste,
        waste_risk_level=risk_level,
        status="remaining"
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

def get_grocery_items(db: Session, user_id: int, search: str = None):
    query = db.query(GroceryItem).filter(GroceryItem.user_id == user_id)
    if search:
        query = query.filter(GroceryItem.item_name.ilike(f"%{search}%"))
    return query.all()

def update_grocery_item(db: Session, item_id: int, item_data: dict, predicted_waste: float = None, risk_level: str = None):
    db_item = db.query(GroceryItem).filter(GroceryItem.id == item_id).first()
    if not db_item:
        return None
    
    db_item.item_name = item_data["item_name"]
    db_item.quantity = item_data["quantity"]
    db_item.purchase_date = date.fromisoformat(item_data["purchase_date"])
    db_item.expiration_date = date.fromisoformat(item_data["expiration_date"])
    
    # If dates changed, we recalculate ML predictions
    if predicted_waste is not None:
        db_item.predicted_waste_percent = predicted_waste
    if risk_level is not None:
        db_item.waste_risk_level = risk_level
        
    db.commit()
    db.refresh(db_item)
    return db_item

def delete_grocery_item(db: Session, item_id: int):
    db_item = db.query(GroceryItem).filter(GroceryItem.id == item_id).first()
    if not db_item:
        return False
    db.delete(db_item)
    db.commit()
    return True

def update_item_status(db: Session, item_id: int, status: str):
    db_item = db.query(GroceryItem).filter(GroceryItem.id == item_id).first()
    if not db_item:
        return None
    db_item.status = status
    if status == "donated":
        db_item.donated_at = datetime.utcnow()
    else:
        db_item.donated_at = None
        
    db.commit()
    db.refresh(db_item)
    return db_item


# --- STATISTICS ---

def get_dashboard_stats(db: Session, user_id: int):
    items = db.query(GroceryItem).filter(GroceryItem.user_id == user_id).all()
    today = date.today()
    
    total_items = len(items)
    expiring_soon = 0
    donated_count = 0
    waste_saved_kg = 0.0
    
    for item in items:
        # Expiring soon: remaining status and within 7 days
        days_left = (item.expiration_date - today).days
        if item.status == "remaining" and 0 <= days_left <= 7:
            expiring_soon += 1
            
        if item.status == "donated":
            donated_count += 1
            # Calculate waste saved: quantity * (predicted waste / 100) or simply the whole quantity
            # Let's count the actual quantity donated as food saved!
            waste_saved_kg += item.quantity
            
    return {
        "total_items": total_items,
        "expiring_soon": expiring_soon,
        "donated_count": donated_count,
        "waste_saved_kg": round(waste_saved_kg, 2)
    }