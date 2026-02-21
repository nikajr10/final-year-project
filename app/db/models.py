from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector  # <-- The Magic Import
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name_nepali = Column(String, unique=True, index=True) # e.g., "Chamal"
    name_english = Column(String)                         # e.g., "Rice"
    unit = Column(String)                                 # e.g., "kg"
    current_stock = Column(Float, default=0.0)
    
    # THE AI BRAIN: This column stores the meaning of the word as numbers
    # 384 is the standard size for 'all-MiniLM-L6-v2' (SBERT)
    embedding = Column(Vector(384)) 

class VoiceLog(Base):
    __tablename__ = "voice_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    original_text = Column(Text)       # What Whisper heard
    corrected_intent = Column(String)  # What Llama extracted (ADD/REMOVE)
    confidence_score = Column(Float)

# --- NEW: USER MODEL FOR AUTHENTICATION ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="admin") # Defaulting to admin for your project