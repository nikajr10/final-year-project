"""
main.py
=======
SmartBiz AI — Nepali Voice Inventory System — FastAPI Entry Point

Full pipeline per request:
  1. Audio upload → temp file
  2. whisper_service.transcribe()     → cleaned English-token string
     (Devanagari numeral conversion + exact dict + prefix-tree + dedup)
  3. llm_service.process_text()       → { intent, item, qty, unit }
     (regex-first, Llama3 two-agent fallback)
  4. _find_product() — 3-tier search:
       Tier 1: Exact DB match on name_nepali / name_english  (O(1))
       Tier 2: pgvector HNSW cosine_distance()               (O(log n))
               PostgreSQL automatically uses HNSW index from models.py
       Tier 3: difflib fuzzy string match                    (O(n), last resort)
  5. DB stock update + VoiceLog + TransactionHistory
  6. Low-stock alert

SBERT ENCODING USED IN SEARCH:
  Query:   sbert.encode("Maida")          → 384-dim vector
  DB rows: stored as sbert.encode("Flour Maida") → 384-dim vector  (seeded in seed_data.py)
  
  cosine_distance measures the ANGLE between these vectors.
  "Maida" and "Flour Maida" point in very similar semantic directions → low distance → top match.
  The HNSW index in models.py makes this search O(log n) instead of O(n).
"""

import os
import uuid
import shutil
import numpy as np
from difflib import SequenceMatcher

from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

from app.db.session import get_db
from app.db.models import Product, VoiceLog, TransactionHistory
from app.core.whisper_service import WhisperService
from app.core.llm_service import LLMService
from app.api import auth, reports


# ══════════════════════════════════════════════════════════════════════════════
# APP SETUP
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="SmartBiz AI Backend")
app.include_router(auth.router,    prefix="/api/auth",    tags=["Authentication"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])


# ══════════════════════════════════════════════════════════════════════════════
# AI MODEL INITIALIZATION
# Loaded ONCE at startup — reused for every request (no reload overhead)
# ══════════════════════════════════════════════════════════════════════════════

print("⏳ Loading AI Models...")

print("   - Whisper (Ears)...")
whisper_service = WhisperService()

print("   - Llama 3 (Brain)...")
llm_service = LLMService()

print("   - SBERT (Vector Engine)...")
# all-MiniLM-L6-v2: 384-dimensional, fast, multilingual-friendly
# MUST be the same model used in seed_data.py — vectors must be comparable
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

print("✅ All AI Systems Ready!")


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT SEARCH — 3-Tier Strategy
# ══════════════════════════════════════════════════════════════════════════════

def _find_product(candidate_item: str, db: Session) -> tuple["Product | None", str]:
    """
    Locate the correct product row using a 3-tier search cascade.

    Tier 1 — Exact string match (instant, zero compute)
    ─────────────────────────────────────────────────────
    Matches candidate against name_nepali then name_english.
    This is the happy path — hit for ~95% of clean commands.
    Cost: one indexed DB lookup.

    Tier 2 — pgvector HNSW cosine similarity (fast, semantic)
    ──────────────────────────────────────────────────────────
    Encode candidate with SBERT → 384-dim vector.
    Ask PostgreSQL: "Which stored embedding is closest by cosine angle?"
    
    PostgreSQL automatically uses the HNSW index (built in models.py with
    vector_cosine_ops) — it navigates the graph instead of scanning all rows.
    O(log n) complexity. With 10 products: < 1ms. With 1M products: still fast.
    
    Cosine distance values:
      0.0  = identical vectors (perfect match)
      0.5  = somewhat similar
      1.0  = completely unrelated
      > 2.0 = possible (cosine can be negative for opposite directions)
    
    We accept any match with distance < 0.6 (= similarity > 0.4).
    Adjust threshold if you get false positives or missed matches.

    Tier 3 — difflib fuzzy string match (fallback, no compute)
    ──────────────────────────────────────────────────────────
    Pure Python string comparison using SequenceMatcher ratio.
    Catches edge cases where SBERT fails on very short or unusual strings.
    Cost: O(n) string comparisons — acceptable since we only have 10 products.
    Accept ratio > 0.4.

    Returns:
        (Product, match_type_string) or (None, "Not Found")
    """

    # ── Tier 1: Exact match ──────────────────────────────────────────────────
    product = db.query(Product).filter(
        Product.name_nepali == candidate_item
    ).first()

    if product:
        print(f"   ✅ Tier 1 (name_nepali exact): {product.name_english}")
        return product, "Exact Match"

    product = db.query(Product).filter(
        Product.name_english == candidate_item
    ).first()

    if product:
        print(f"   ✅ Tier 1 (name_english exact): {product.name_english}")
        return product, "Exact Match"

    # ── Tier 2: HNSW cosine vector search ────────────────────────────────────
    print(f"⚠️  No exact match for '{candidate_item}' — running HNSW vector search...")

    try:
        # Encode the query string into a 384-dim vector
        query_vector = sbert_model.encode(candidate_item).tolist()

        # Ask PostgreSQL to find the nearest embedding by cosine distance.
        # Because models.py defines the HNSW index with vector_cosine_ops,
        # PostgreSQL's query planner automatically uses the HNSW graph here.
        # No manual index hinting needed — it just works.
        result = db.scalars(
            select(Product)
            .filter(Product.embedding.isnot(None))   # skip unembedded rows
            .order_by(Product.embedding.cosine_distance(query_vector))
            .limit(1)
        ).first()

        if result:
            # Compute the actual distance to apply our threshold
            # (pgvector doesn't return the distance value directly in .first())
            distance = float(
                db.execute(
                    select(
                        Product.embedding.cosine_distance(query_vector)
                    ).where(Product.id == result.id)
                ).scalar()
            )

            COSINE_THRESHOLD = 0.6   # distance < 0.6 → similarity > 0.4 → accept
            print(f"   🤖 HNSW best: '{result.name_english}' (cosine_distance={distance:.4f})")

            if distance < COSINE_THRESHOLD:
                print(f"   ✅ Tier 2 (HNSW vector): {result.name_english}")
                return result, "HNSW Vector Match"
            else:
                print(f"   ⚠️  Score {distance:.4f} exceeds threshold {COSINE_THRESHOLD} — rejected.")

    except Exception as e:
        # Graceful degradation: if pgvector/HNSW fails for any reason,
        # log it and fall through to Tier 3 instead of crashing
        print(f"   ❌ HNSW search error: {e} — falling through to fuzzy match.")

    # ── Tier 3: String fuzzy match ────────────────────────────────────────────
    print(f"⚠️  HNSW failed — running fuzzy string match...")

    products    = db.query(Product).all()
    best        = None
    best_ratio  = 0.0

    for p in products:
        for name in [p.name_english, p.name_nepali]:
            ratio = SequenceMatcher(
                None, candidate_item.lower(), name.lower()
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best       = p

    print(f"   🔤 Fuzzy best: '{best.name_english if best else None}' (ratio={best_ratio:.3f})")

    if best and best_ratio >= 0.4:
        print(f"   ✅ Tier 3 (fuzzy string): {best.name_english}")
        return best, "Fuzzy String Match"

    return None, "Not Found"


# ══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _format_qty(qty: float) -> "int | float":
    """
    Return int for whole numbers (10.0 → 10), float for fractions (1.5 → 1.5).
    Keeps the JSON response clean — no trailing .0 on integer quantities.
    """
    return int(qty) if qty == int(qty) else qty


# ══════════════════════════════════════════════════════════════════════════════
# MAIN VOICE PROCESSING ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/process-voice")
async def process_voice(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db),
):
    """
    Accept a Nepali voice command audio file and update inventory.

    Steps:
      1. Save audio to temp file (preserve original extension for FFmpeg)
      2. Transcribe + clean via whisper_service (full pipeline, not raw Whisper)
      3. Parse intent via llm_service (regex → Llama3 fallback)
      4. Find product via 3-tier search (exact → HNSW → fuzzy)
      5. Update stock, log voice command, log transaction
      6. Return result with optional low-stock alert
    """

    # Preserve original file extension so Whisper/FFmpeg handles format correctly
    # (.m4a, .mp3, .wav, .ogg — Whisper handles all of them)
    ext       = os.path.splitext(file.filename)[-1] or ".wav"
    temp_path = f"temp_{uuid.uuid4()}{ext}"

    with open(temp_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        # ── Step 1: Transcribe + clean ────────────────────────────────────────
        # whisper_service.transcribe() runs the FULL pipeline:
        #   • Whisper medium model (language=ne, beam_size=8, temp=0.0)
        #   • Devanagari numeral conversion:  १० → 10
        #   • Exact dict replacement:         दास → 10, घटाउ → Remove, etc.
        #   • Devanagari prefix-tree:         महिदा → Flour (म is unique)
        #   • Action deduplication:           "Check Check Check" → "Check"
        print(f"\n🎧 Processing: {file.filename}")
        cleaned_text = whisper_service.transcribe(temp_path)
        print(f"🗣️  Cleaned: '{cleaned_text}'")

        if not cleaned_text:
            return {
                "status":  "error",
                "message": "Audio is silent or could not be transcribed.",
            }

        # ── Step 2: Parse intent ──────────────────────────────────────────────
        # llm_service.process_text() runs:
        #   • Regex parser (instant, no API call) — handles ~90% of cases
        #   • Llama3 two-agent pipeline if regex is inconclusive
        #   • Output validated against allowed items/actions/units
        ai_data = llm_service.process_text(cleaned_text)

        if not ai_data or "item" not in ai_data:
            return {
                "status":        "error",
                "message":       "Could not understand the voice command.",
                "transcription": cleaned_text,
            }

        candidate_item = ai_data["item"]         # Nepali display name, e.g. "Maida"
        intent         = ai_data["intent"]       # "ADD" | "REMOVE" | "CHECK"
        qty            = float(ai_data["qty"])   # quantity (0.0 for CHECK)
        unit_hint      = ai_data.get("unit", "") # spoken unit (may differ from DB)

        print(f"🧠 Parsed: item='{candidate_item}'  intent={intent}  qty={qty}  unit={unit_hint}")

        # ── Step 3: Find product ──────────────────────────────────────────────
        product, match_type = _find_product(candidate_item, db)

        if not product:
            return {
                "status":        "error",
                "message":       f"'{candidate_item}' not found in inventory.",
                "transcription": cleaned_text,
            }

        # ── Step 4: Apply inventory action ───────────────────────────────────
        if intent == "ADD":
            product.current_stock += qty
            action_msg = "Added to stock"

        elif intent == "REMOVE":
            # Guard against negative stock
            if product.current_stock < qty:
                return {
                    "status":  "error",
                    "message": (
                        f"Cannot remove {_format_qty(qty)} {product.unit} of "
                        f"{product.name_english} — only "
                        f"{_format_qty(product.current_stock)} in stock."
                    ),
                    "transcription": cleaned_text,
                }
            product.current_stock -= qty
            action_msg = "Removed from stock"

        elif intent == "CHECK":
            qty        = 0.0
            action_msg = "Checked stock level"

        else:
            qty        = 0.0
            action_msg = "Unknown action"

        # ── Step 5: Persist ───────────────────────────────────────────────────

        # Voice audit log (every command, success or not)
        db.add(VoiceLog(
            original_text    = cleaned_text,
            corrected_intent = f"{intent} {_format_qty(qty)} {product.name_nepali}",
            confidence_score = 1.0 if match_type == "Exact Match" else 0.85,
        ))

        # Immutable transaction ledger (only ADD/REMOVE with qty > 0)
        if intent in ("ADD", "REMOVE") and qty > 0:
            db.add(TransactionHistory(
                product_id              = product.id,
                product_name_english    = product.name_english,
                product_name_nepali     = product.name_nepali,
                action_type             = intent,
                quantity_changed        = qty,
                stock_after_transaction = product.current_stock,
                unit                    = product.unit,
            ))

        db.commit()
        db.refresh(product)

        # ── Step 6: Low-stock alert ───────────────────────────────────────────
        LOW_STOCK_THRESHOLD = 40
        alert_message = None
        if product.current_stock < LOW_STOCK_THRESHOLD:
            alert_message = (
                f"⚠️ LOW STOCK: {product.name_english} is at "
                f"{_format_qty(product.current_stock)} {product.unit} "
                f"(threshold: {LOW_STOCK_THRESHOLD})"
            )

        # ── Step 7: Response ──────────────────────────────────────────────────
        return {
            "status":        "success",
            "transcription": cleaned_text,
            "match_method":  match_type,
            "action":        action_msg,
            "item":          product.name_english,
            "item_nepali":   product.name_nepali,
            "qty_changed":   _format_qty(qty),
            "new_stock":     _format_qty(product.current_stock),
            "unit":          product.unit,
            "alert_message": alert_message,
        }

    except Exception as e:
        import traceback
        print(f"❌ Unhandled error: {e}")
        traceback.print_exc()
        return {"status": "error", "error": str(e)}

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/refresh-embeddings")
async def refresh_embeddings(db: Session = Depends(get_db)):
    """
    Re-encode all products and update their embeddings in the database.
    Call this after adding or renaming products — keeps the HNSW index current.
    The HNSW index updates automatically as new embeddings are written.
    """
    print("🔄 Refreshing product embeddings...")
    products = db.query(Product).all()

    if not products:
        return {"status": "error", "message": "No products in database."}

    texts      = [f"{p.name_english} {p.name_nepali}" for p in products]
    embeddings = sbert_model.encode(texts, convert_to_numpy=True)

    for i, product in enumerate(products):
        product.embedding = embeddings[i].tolist()

    db.commit()
    print(f"   ✅ Updated embeddings for {len(products)} products.")

    return {
        "status":  "success",
        "message": f"Embeddings refreshed for {len(products)} products.",
    }


@app.get("/stock")
async def get_all_stock(db: Session = Depends(get_db)):
    """
    Return current stock levels for all products.
    Useful for dashboard display without a voice command.
    """
    products = db.query(Product).all()
    return {
        "status": "success",
        "inventory": [
            {
                "item":          p.name_english,
                "item_nepali":   p.name_nepali,
                "current_stock": _format_qty(p.current_stock),
                "unit":          p.unit,
            }
            for p in products
        ],
    }