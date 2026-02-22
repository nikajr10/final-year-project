from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name_nepali = Column(String, unique=True, index=True) 
    name_english = Column(String)                         
    unit = Column(String)                                 
    current_stock = Column(Float, default=0.0)
    embedding = Column(Vector(384)) 

class VoiceLog(Base):
    __tablename__ = "voice_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    original_text = Column(Text)       
    corrected_intent = Column(String)  
    confidence_score = Column(Float)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="admin") 

# --- NEW: THE INVENTORY LEDGER ---
class TransactionHistory(Base):
    __tablename__ = "transaction_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    product_id = Column(Integer, ForeignKey("products.id"))
    product_name_english = Column(String)
    product_name_nepali = Column(String)
    action_type = Column(String) # Will strictly be "ADD" or "REMOVE"
    quantity_changed = Column(Float)
    stock_after_transaction = Column(Float)
    unit = Column(String)