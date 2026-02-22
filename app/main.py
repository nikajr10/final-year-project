"""
main.py
=======
Nepali Voice Inventory Management System — FastAPI Entry Point

Pipeline per request:
  1. Save uploaded audio to temp file
  2. whisper_service.transcribe()  →  cleaned English-token string
                                      (prefix-tree + number conversion + dedup)
  3. llm_service.process_text()   →  { intent, item, qty, unit }
                                      (regex-first, Llama3 fallback)
  4. _find_product()              →  Product row from DB
       a. Exact match  on name_nepali
       b. SBERT semantic match    (in-memory cosine similarity, no pgvector)
       c. String fuzzy match      (difflib, last resort)
  5. DB update + Transaction log
  6. Alert if stock below threshold
"""

import os
import uuid
import shutil
import numpy as np
from difflib import SequenceMatcher

from fastapi import FastAPI, UploadFile, File, Depends
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
# MODEL INITIALIZATION  (loaded once at startup, reused for every request)
# ══════════════════════════════════════════════════════════════════════════════

print("⏳ Loading AI Models...")

print("   - Whisper (Ears)...")
whisper_service = WhisperService()

print("   - Llama 3 (Brain)...")
llm_service = LLMService()

print("   - SBERT (Vector Matcher)...")
# all-MiniLM-L6-v2: fast, lightweight, good multilingual semantic understanding
# 384-dimensional embeddings, cosine similarity works perfectly
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

# In-memory product embedding cache — built once, reused forever
# Structure: [ { "product": Product, "embedding": np.array } ]
# Populated lazily on first request (DB not ready at import time)
_product_cache: list[dict] = []
_cache_built   = False

print("✅ All AI Systems Ready!")


# ══════════════════════════════════════════════════════════════════════════════
# SBERT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Pure NumPy cosine similarity.
    Returns a value in [-1, 1] where 1.0 = identical direction.
    Does NOT require pgvector or any DB extension.
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _build_product_cache(db: Session) -> None:
    """
    Load every product from the DB and encode its combined name.
    Called once per process lifetime (guarded by _cache_built flag).

    Encoding strategy:
      We encode BOTH the English and Nepali names together as one string:
        "Rice Chamal"   — so queries like "Rice" AND "Chamal" both match well.
        "Flour Maida"   — covers both languages in one vector.
      This is better than encoding just one language because:
        - whisper_service output might be English ("Flour") or Nepali ("Maida")
        - SBERT can find the right product regardless of which comes out
    """
    global _product_cache, _cache_built

    products = db.query(Product).all()
    if not products:
        print("⚠️  No products in DB — SBERT cache is empty.")
        _cache_built = True
        return

    # Build text representations for each product
    texts = [
        f"{p.name_english} {p.name_nepali}"
        for p in products
    ]

    # Batch encode all products in one call (much faster than one by one)
    embeddings = sbert_model.encode(texts, convert_to_numpy=True)

    _product_cache = [
        {"product": p, "embedding": embeddings[i]}
        for i, p in enumerate(products)
    ]

    _cache_built = True
    print(f"   🔢 SBERT cache built: {len(_product_cache)} products encoded.")


def _sbert_match(candidate: str, threshold: float = 0.35) -> Product | None:
    """
    Find the best matching product using SBERT cosine similarity.

    Args:
        candidate   : The item name from LLM output (e.g. "Maida", "Flour", "Chiura")
        threshold   : Minimum cosine similarity to accept a match (0.35 is generous
                      enough for short grocery words; raise to 0.5 if false positives occur)

    Returns:
        Best matching Product, or None if no match above threshold.

    How it works:
        1. Encode the candidate string into a 384-dim vector using SBERT
        2. Compare against every cached product embedding via cosine similarity
        3. Return the product with the highest similarity if it's above threshold
    """
    if not _product_cache:
        return None

    # Encode the query (fast — single short string)
    query_vec = sbert_model.encode(candidate, convert_to_numpy=True)

    best_product   = None
    best_score     = -1.0

    for entry in _product_cache:
        score = _cosine_similarity(query_vec, entry["embedding"])
        if score > best_score:
            best_score   = score
            best_product = entry["product"]

    print(f"   🤖 SBERT best match: '{best_product.name_english if best_product else None}'"
          f" (score={best_score:.3f}, threshold={threshold})")

    if best_score >= threshold:
        return best_product
    return None


def _fuzzy_string_match(candidate: str, db: Session) -> Product | None:
    """
    Last-resort fallback: pure string similarity using difflib.
    Compares candidate against EVERY product's English and Nepali name.
    Returns the best match if similarity > 0.4, else None.

    This catches cases where SBERT fails on very short or unusual strings.
    """
    products    = db.query(Product).all()
    best        = None
    best_ratio  = 0.0

    for p in products:
        # Compare against both name variants
        for name in [p.name_english, p.name_nepali]:
            ratio = SequenceMatcher(None, candidate.lower(), name.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best       = p

    print(f"   🔤 Fuzzy string match: '{best.name_english if best else None}'"
          f" (ratio={best_ratio:.3f})")

    return best if best_ratio >= 0.4 else None


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT FINDER — 3-tier search strategy
# ══════════════════════════════════════════════════════════════════════════════

def _find_product(candidate_item: str, db: Session) -> tuple[Product | None, str]:
    """
    Find the right product row using a 3-tier strategy:

    Tier 1 — Exact match on name_nepali (fastest, zero compute)
              Also tries name_english as fallback within exact match.
    Tier 2 — SBERT semantic similarity (handles typos, alternate names, language mix)
    Tier 3 — difflib string fuzzy match (last resort for very short strings)

    Returns:
        (product, match_type_string) or (None, "Not Found")
    """

    # ── Tier 1: Exact match ──────────────────────────────────────────────────
    product = db.query(Product).filter(
        Product.name_nepali == candidate_item
    ).first()

    if product:
        print(f"   ✅ Tier 1 exact match (name_nepali): {product.name_english}")
        return product, "Exact Match"

    # Try English name too (in case LLM output was English canonical)
    product = db.query(Product).filter(
        Product.name_english == candidate_item
    ).first()

    if product:
        print(f"   ✅ Tier 1 exact match (name_english): {product.name_english}")
        return product, "Exact Match"

    # ── Tier 2: SBERT semantic match ─────────────────────────────────────────
    print(f"⚠️  Exact match failed for '{candidate_item}' — trying SBERT...")
    product = _sbert_match(candidate_item)

    if product:
        print(f"   ✅ Tier 2 SBERT match: {product.name_english}")
        return product, "SBERT Semantic Match"

    # ── Tier 3: String fuzzy match ───────────────────────────────────────────
    print(f"⚠️  SBERT failed — trying fuzzy string match...")
    product = _fuzzy_string_match(candidate_item, db)

    if product:
        print(f"   ✅ Tier 3 fuzzy match: {product.name_english}")
        return product, "Fuzzy String Match"

    return None, "Not Found"


# ══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _format_qty(qty: float) -> int | float:
    """Return int if qty is a whole number, float otherwise. Keeps JSON clean."""
    return int(qty) if qty == int(qty) else qty


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/process-voice")
async def process_voice(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db)
):
    """
    Process a Nepali voice command and update inventory.

    Full pipeline:
      Audio file → Whisper (transcribe + clean) → LLM (parse intent)
      → DB product lookup (exact → SBERT → fuzzy)
      → Stock update + Transaction log + Alert
    """

    # ── Build SBERT cache on first request (DB is ready by then) ─────────────
    global _cache_built
    if not _cache_built:
        _build_product_cache(db)

    # ── Save uploaded audio to a temp file ───────────────────────────────────
    # Keep the original extension so Whisper/FFmpeg handles format correctly
    ext          = os.path.splitext(file.filename)[-1] or ".wav"
    temp_path    = f"temp_{uuid.uuid4()}{ext}"

    with open(temp_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        # ── Step 1: Transcribe + clean ────────────────────────────────────────
        # whisper_service.transcribe() runs:
        #   - Whisper model (Nepali language, beam_size=8)
        #   - Devanagari numeral conversion (१० → 10)
        #   - Exact dict substitution (all item/action/unit/number variants)
        #   - Prefix-tree for unknown Devanagari words
        #   - Deduplication of repeated action tokens
        print(f"\n🎧 Processing Audio: {file.filename}")

        cleaned_text = whisper_service.transcribe(temp_path)
        print(f"🗣️  Cleaned text: '{cleaned_text}'")

        if not cleaned_text:
            return {
                "status": "error",
                "message": "Could not transcribe audio — file may be silent or corrupt."
            }

        # ── Step 2: Parse intent with LLM ────────────────────────────────────
        # llm_service.process_text() runs:
        #   - Regex parser first (instant, no Ollama call)
        #   - Ollama/Llama3 two-agent pipeline if regex inconclusive
        #   - Output validated and sanitised
        ai_data = llm_service.process_text(cleaned_text)

        if not ai_data or "item" not in ai_data:
            return {
                "status": "error",
                "message": "Could not understand the command.",
                "transcription": cleaned_text
            }

        candidate_item = ai_data["item"]        # Nepali display name e.g. "Maida"
        intent         = ai_data["intent"]      # "ADD" | "REMOVE" | "CHECK"
        qty            = float(ai_data["qty"])  # quantity, 0 for CHECK
        unit_hint      = ai_data.get("unit", "") # unit from voice, may differ from DB

        print(f"🧠 LLM parsed: item='{candidate_item}'  intent={intent}  qty={qty}  unit={unit_hint}")

        # ── Step 3: Find the product ──────────────────────────────────────────
        product, match_type = _find_product(candidate_item, db)

        if not product:
            return {
                "status": "error",
                "message": f"Item '{candidate_item}' not found in inventory.",
                "transcription": cleaned_text
            }

        # ── Step 4: Apply inventory action ───────────────────────────────────
        if intent == "ADD":
            product.current_stock += qty
            action_msg = "Added to stock"

        elif intent == "REMOVE":
            if product.current_stock < qty:
                # Don't allow negative stock — warn but don't crash
                return {
                    "status": "error",
                    "message": (
                        f"Cannot remove {_format_qty(qty)} {product.unit} of "
                        f"{product.name_english} — only {product.current_stock} in stock."
                    ),
                    "transcription": cleaned_text
                }
            product.current_stock -= qty
            action_msg = "Removed from stock"

        elif intent == "CHECK":
            qty        = 0.0
            action_msg = "Checked stock level"

        else:
            action_msg = "Unknown action"
            qty        = 0.0

        # ── Step 5: Persist to database ───────────────────────────────────────

        # Voice log — raw + corrected for audit trail
        db.add(VoiceLog(
            original_text    = cleaned_text,
            corrected_intent = f"{intent} {_format_qty(qty)} {product.name_nepali}",
            confidence_score = 1.0 if match_type == "Exact Match" else 0.85
        ))

        # Transaction ledger — only for stock-changing actions
        if intent in ("ADD", "REMOVE") and qty > 0:
            db.add(TransactionHistory(
                product_id              = product.id,
                product_name_english    = product.name_english,
                product_name_nepali     = product.name_nepali,
                action_type             = intent,
                quantity_changed        = qty,
                stock_after_transaction = product.current_stock,
                unit                    = product.unit
            ))

        db.commit()
        db.refresh(product)

        # ── Step 6: Low-stock alert ───────────────────────────────────────────
        LOW_STOCK_THRESHOLD = 40
        alert_message = None
        if product.current_stock < LOW_STOCK_THRESHOLD:
            alert_message = (
                f"⚠️ LOW STOCK: {product.name_english} is at "
                f"{product.current_stock} {product.unit} "
                f"(threshold: {LOW_STOCK_THRESHOLD})"
            )

        # ── Step 7: Return response ───────────────────────────────────────────
        return {
            "status":       "success",
            "transcription": cleaned_text,
            "match_method":  match_type,
            "action":        action_msg,
            "item":          product.name_english,
            "item_nepali":   product.name_nepali,
            "qty_changed":   _format_qty(qty),
            "new_stock":     product.current_stock,
            "unit":          product.unit,
            "alert_message": alert_message
        }

    except Exception as e:
        import traceback
        print(f"❌ Unhandled error: {e}")
        traceback.print_exc()
        return {"status": "error", "error": str(e)}

    finally:
        # Always clean up the temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ══════════════════════════════════════════════════════════════════════════════
# SBERT CACHE REFRESH ENDPOINT (optional — call after adding new products)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/refresh-embeddings")
async def refresh_embeddings(db: Session = Depends(get_db)):
    """
    Rebuild the in-memory SBERT product embedding cache.
    Call this after adding or renaming products in the database.
    """
    global _cache_built
    _cache_built = False
    _product_cache.clear()
    _build_product_cache(db)
    return {
        "status":  "success",
        "message": f"SBERT cache rebuilt with {len(_product_cache)} products."
    }