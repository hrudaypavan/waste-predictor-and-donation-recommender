from sqlalchemy import Column, Integer, String, Date, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    groceries = relationship("GroceryItem", back_populates="owner", cascade="all, delete-orphan")


class GroceryItem(Base):
    __tablename__ = "groceries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)  # Float to allow fractional kg/liters
    purchase_date = Column(Date, nullable=False)
    expiration_date = Column(Date, nullable=False)
    predicted_waste_percent = Column(Float, default=0.0)
    waste_risk_level = Column(String, default="Low")  # Low, Medium, High
    status = Column(String, default="remaining")      # remaining, wasted, donated
    donated_at = Column(DateTime, nullable=True)      # Timestamp when marked donated

    owner = relationship("User", back_populates="groceries")