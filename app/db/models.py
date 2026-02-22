"""
app/db/models.py
================
SQLAlchemy ORM models for SmartBiz AI Inventory System.

KEY ADDITION — HNSW Index on Product.embedding:
------------------------------------------------
HNSW (Hierarchical Navigable Small World) is a graph-based approximate
nearest-neighbour algorithm built into pgvector.

Without HNSW: PostgreSQL scans ALL rows and computes cosine distance
              for each one. O(n) — slow as product count grows.

With HNSW:    PostgreSQL navigates a pre-built multi-layer graph,
              jumping directly to the nearest neighbours. O(log n) —
              1 million products searched as fast as 1,000.

Parameters explained:
  m=16              — Each node in the graph connects to 16 neighbours.
                      Higher = better recall, more memory. 16 is the
                      standard default for most use cases.
  ef_construction=64 — Candidate list size when BUILDING the graph.
                       Higher = more accurate graph, slower to build.
                       64 is a safe default. Only matters at index build
                       time, not at query time.

vector_cosine_ops:
  Tells the HNSW graph to use COSINE DISTANCE as its metric.
  This is critical — it must match how you query:
    Product.embedding.cosine_distance(query_vector)
  
  WHY cosine for text embeddings:
  - Only measures the ANGLE between vectors (semantic direction)
  - Ignores vector magnitude (length of the text doesn't matter)
  - "Rice Chamal" and "Rice" point in the same semantic direction
  - Perfect for SBERT embeddings

  If you used euclidean_ops here but cosine_distance() in queries,
  the HNSW index would be IGNORED by the query planner — slow!
  They MUST match.
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
    unit          = Column(String,  nullable=False)          # kg / pieces / packet / liter
    current_stock = Column(Float,   default=0.0)

    # 384-dimensional SBERT vector (all-MiniLM-L6-v2 output size)
    # Stores the combined "name_english name_nepali" embedding
    # so both English and Nepali queries resolve correctly.
    embedding = Column(Vector(384))

    # ── HNSW Index ────────────────────────────────────────────────────────────
    # Attached directly to the table so SQLAlchemy creates it via create_all().
    # postgresql_using='hnsw'  → use HNSW algorithm (not IVFFlat)
    # m=16                     → graph connectivity (neighbours per node)
    # ef_construction=64       → build-time accuracy (higher=better graph)
    # vector_cosine_ops        → optimise for COSINE distance queries
    #
    # After this index exists, the query:
    #   select(Product).order_by(Product.embedding.cosine_distance(vec)).limit(1)
    # automatically uses HNSW — no code change needed at query time.
    __table_args__ = (
        Index(
            "hnsw_product_embedding_idx",       # index name (must be unique in DB)
            "embedding",                         # column to index
            postgresql_using="hnsw",             # algorithm
            postgresql_with={
                "m": 16,                         # neighbour connections per node
                "ef_construction": 64,           # build-time candidate list size
            },
            postgresql_ops={
                "embedding": "vector_cosine_ops" # MUST match cosine_distance() queries
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
# VOICE LOG  — audit trail of every voice command received
# ══════════════════════════════════════════════════════════════════════════════

class VoiceLog(Base):
    __tablename__ = "voice_logs"

    id               = Column(Integer,  primary_key=True, index=True)
    timestamp        = Column(DateTime, default=datetime.utcnow)
    original_text    = Column(Text)       # cleaned whisper output
    corrected_intent = Column(String)     # e.g. "ADD 10 Maida"
    confidence_score = Column(Float)      # 1.0 = exact match, 0.85 = vector match


# ══════════════════════════════════════════════════════════════════════════════
# USER — authentication
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String,  unique=True, index=True)
    email           = Column(String,  unique=True, index=True)
    hashed_password = Column(String)
    role            = Column(String,  default="admin")


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTION HISTORY — immutable ledger of every stock change
# ══════════════════════════════════════════════════════════════════════════════

class TransactionHistory(Base):
    __tablename__ = "transaction_history"

    id                      = Column(Integer,  primary_key=True, index=True)
    timestamp               = Column(DateTime, default=datetime.utcnow)
    product_id              = Column(Integer,  ForeignKey("products.id"))
    product_name_english    = Column(String)
    product_name_nepali     = Column(String)
    action_type             = Column(String)   # strictly "ADD" or "REMOVE"
    quantity_changed        = Column(Float)
    stock_after_transaction = Column(Float)
    unit                    = Column(String)