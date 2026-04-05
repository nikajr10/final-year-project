"""
app/db/models.py
================
SQLAlchemy ORM models for SmartBiz AI Inventory System.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector


Base = declarative_base()


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT
# ══════════════════════════════════════════════════════════════════════════════

class Product(Base):
    __tablename__ = "products"

    id            = Column(Integer, primary_key=True, index=True)
    name_nepali   = Column(String,  unique=True, index=True, nullable=False)
    name_english  = Column(String,  nullable=False)
    unit          = Column(String,  nullable=False)
    current_stock = Column(Float,   default=0.0)

    # ── NEW: pricing columns ──────────────────────────────────────────────────
    cost_price    = Column(Float,   default=0.0, nullable=True)   # what you paid per unit
    selling_price = Column(Float,   default=0.0, nullable=True)   # what you sell per unit
    # ─────────────────────────────────────────────────────────────────────────

    # 384-dimensional SBERT vector (all-MiniLM-L6-v2)
    embedding = Column(Vector(384))

    __table_args__ = (
        Index(
            "hnsw_product_embedding_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={
                "m": 16,
                "ef_construction": 64,
            },
            postgresql_ops={
                "embedding": "vector_cosine_ops"
            },
        ),
    )

    def __repr__(self):
        return (
            f"<Product id={self.id} "
            f"name_english='{self.name_english}' "
            f"name_nepali='{self.name_nepali}' "
            f"stock={self.current_stock} {self.unit}>"
        )


# ══════════════════════════════════════════════════════════════════════════════
# VOICE LOG
# ══════════════════════════════════════════════════════════════════════════════

class VoiceLog(Base):
    __tablename__ = "voice_logs"

    id               = Column(Integer,  primary_key=True, index=True)
    timestamp        = Column(DateTime, default=datetime.utcnow)
    original_text    = Column(Text)
    corrected_intent = Column(String)
    confidence_score = Column(Float)


# ══════════════════════════════════════════════════════════════════════════════
# USER
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String,  unique=True, index=True)
    email           = Column(String,  unique=True, index=True)
    hashed_password = Column(String)
    role            = Column(String,  default="admin")


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTION HISTORY
# ══════════════════════════════════════════════════════════════════════════════

class TransactionHistory(Base):
    __tablename__ = "transaction_history"

    id                      = Column(Integer,  primary_key=True, index=True)
    timestamp               = Column(DateTime, default=datetime.utcnow)
    product_id              = Column(Integer,  ForeignKey("products.id"))
    product_name_english    = Column(String)
    product_name_nepali     = Column(String)
    action_type             = Column(String)
    quantity_changed        = Column(Float)
    stock_after_transaction = Column(Float)
    unit                    = Column(String)