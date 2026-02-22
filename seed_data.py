"""
seed_data.py
============
Database initialisation for SmartBiz AI Inventory System.

Run this ONCE before starting the server:
  python seed_data.py

What it does:
  1. Enables the pgvector extension in PostgreSQL
     (required before any Vector column or HNSW index can be created)
  2. Creates all tables via SQLAlchemy (including the HNSW index from models.py)
  3. Encodes each product's combined name with SBERT → stores in embedding column
     (required so pgvector HNSW search has vectors to compare against)
  4. Seeds the 10 default inventory products with starting stock

EMBEDDING STRATEGY:
  We encode: f"{name_english} {name_nepali}"
  Example:   "Flour Maida"  →  384-dim vector
  
  WHY both names together?
  - Voice input from whisper_service may produce English ("Flour") or
    Nepali romanized ("Maida") or mixed — encoding both in one vector
    means cosine_distance() will find the right product regardless.
  - If we only encoded the English name, "Maida" queries would score low.
  - If we only encoded the Nepali name, "Flour" queries would score low.
  - Together: best of both worlds.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer

from app.db.models import Base, Product
from app.core.config import settings   # adjust import to match your project structure


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTS MASTER LIST
# English name, Nepali name, default unit, starting stock
# ══════════════════════════════════════════════════════════════════════════════

PRODUCTS = [
    # ( name_english,  name_nepali,  unit,      starting_stock )
    ("Rice",        "Chamal",   "kg",      100.0),
    ("Lentils",     "Daal",     "kg",      100.0),
    ("Salt",        "Nun",      "kg",      100.0),
    ("Sugar",       "Chini",    "kg",      100.0),
    ("Oil",         "Tel",      "liter",   100.0),
    ("Flour",       "Maida",    "kg",      100.0),
    ("Turmeric",    "Besar",    "kg",      100.0),
    ("Eggs",        "Anda",     "pieces",  100.0),
    ("Beaten Rice", "Chiura",   "kg",      100.0),
    ("Biscuits",    "Biskut",   "packet",  100.0),
]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SEED FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def seed():
    print("🚀 Starting database initialisation...")

    # ── Connect ───────────────────────────────────────────────────────────────
    engine  = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db      = Session()

    # ── Step 1: Enable pgvector extension ─────────────────────────────────────
    # THIS MUST RUN BEFORE Base.metadata.create_all()
    # Without it, the Vector column type and HNSW index in models.py will fail
    # with: "type 'vector' does not exist"
    #
    # IF NOT EXISTS means it's safe to run multiple times — no error if already enabled.
    print("📦 Enabling pgvector extension...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    print("   ✅ pgvector extension ready.")

    # ── Step 2: Create tables + HNSW index ────────────────────────────────────
    # SQLAlchemy reads models.py and creates:
    #   - products table with embedding Vector(384) column
    #   - hnsw_product_embedding_idx with vector_cosine_ops
    #   - voice_logs, users, transaction_history tables
    print("🗂️  Creating tables and HNSW index...")
    Base.metadata.create_all(engine)
    print("   ✅ Tables and HNSW index created.")

    # ── Step 3: Load SBERT model ──────────────────────────────────────────────
    # Same model used in main.py — MUST be identical so vectors are comparable
    # all-MiniLM-L6-v2 → 384-dimensional embeddings
    print("🧠 Loading SBERT model for embedding generation...")
    sbert = SentenceTransformer("all-MiniLM-L6-v2")
    print("   ✅ SBERT loaded.")

    # ── Step 4: Build embedding texts ─────────────────────────────────────────
    # Encode ALL products in a single batch call (much faster than one by one)
    embed_texts = [
        f"{name_en} {name_ne}"
        for name_en, name_ne, _, _ in PRODUCTS
    ]

    print(f"🔢 Encoding {len(embed_texts)} product embeddings...")
    embeddings = sbert.encode(embed_texts, convert_to_numpy=True)
    print(f"   ✅ Embeddings shape: {embeddings.shape}")  # should be (10, 384)

    # ── Step 5: Seed products ─────────────────────────────────────────────────
    print("🌱 Seeding products...")
    seeded = 0
    skipped = 0

    for i, (name_en, name_ne, unit, stock) in enumerate(PRODUCTS):
        # Check if already exists — safe to run seed multiple times
        existing = db.query(Product).filter(
            Product.name_nepali == name_ne
        ).first()

        if existing:
            # Update embedding in case SBERT model changed
            existing.embedding = embeddings[i].tolist()
            print(f"   ⟳  Updated embedding for '{name_en}' (already exists)")
            skipped += 1
        else:
            product = Product(
                name_english  = name_en,
                name_nepali   = name_ne,
                unit          = unit,
                current_stock = stock,
                embedding     = embeddings[i].tolist(),  # list of 384 floats
            )
            db.add(product)
            print(f"   ✅ Seeded: {name_en} ({name_ne}) — {stock} {unit}")
            seeded += 1

    db.commit()
    db.close()

    print(f"\n✅ Seed complete: {seeded} new products, {skipped} updated.")
    print("   HNSW index is now populated and ready for fast cosine search.")
    print("   Run: uvicorn app.main:app --reload")


if __name__ == "__main__":
    seed() 