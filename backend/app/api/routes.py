"""
routes.py
=========
SmartBiz AI — Voice Transaction API Routes

Full pipeline per POST /voice-transaction request:
  1. Receive audio UploadFile from React Native
  2. Save to temp file (preserves extension for FFmpeg/Whisper)
  3. WhisperService.transcribe()  →  (cleaned_text, quantity)
     • Devanagari numeral conversion  (१० → 10)
     • Exact dict replacement         (घटाउ → Remove, बिस्कुट → Biscuits)
     • Devanagari prefix-tree         (महिदा → Flour)
     • Synonym disambiguation         (Biscuits → Digestive Biscuit)
     • Quantity extraction            ("10 packet ..." → qty=10)
  4. VectorMatcher.find_best_match()  →  product_id  (≥90% similarity or None)
  5. Route intent to crud.deduct_inventory / add_inventory / get_stock
  6. Return standard JSON envelope to React Native
  7. Always delete temp file (success or failure)
"""

from __future__ import annotations

import os
import uuid
import shutil

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.whisper_service import WhisperService
from app.core.vector_matcher import VectorMatcher
from app.db import crud


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# AI SERVICE SINGLETONS
# Loaded once when this module is first imported by main.py.
# Re-using these instances across every request avoids the heavy model-reload
# overhead (Whisper medium = ~1.5 GB; SBERT = ~90 MB).
# ══════════════════════════════════════════════════════════════════════════════

print("⏳ routes.py — loading AI services...")
_whisper = WhisperService()
_matcher = VectorMatcher()
print("✅ routes.py — AI services ready.")


# ══════════════════════════════════════════════════════════════════════════════
# VOICE TRANSACTION ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/voice-transaction")
async def voice_transaction(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db),
):
    """
    Accept a Nepali voice command and execute the matching inventory action.

    Request
    -------
    POST multipart/form-data
        file : audio file (.wav | .m4a | .mp3 | .ogg)

    Success Response
    ----------------
    {
        "status":        "success",
        "transcription": "10 packet Digestive Biscuit Remove",
        "intent":        "REMOVE",
        "item":          "Digestive Biscuit",
        "item_nepali":   "डाइजेस्टिभ बिस्कुट",
        "qty_changed":   10,
        "new_stock":     33,
        "unit":          "packet",
        "message":       "Removed 10 packet of 'Digestive Biscuit'. 33 packet remaining."
    }

    Error Response
    --------------
    {
        "status":        "error",
        "message":       "<human-readable reason>",
        "transcription": "<if available>"
    }
    """

    # ── Save to temp file ─────────────────────────────────────────────────────
    # Preserve original extension so Whisper/FFmpeg handles codec correctly.
    # (.m4a from iOS, .webm from Android, .wav from web — Whisper handles all)
    ext       = os.path.splitext(file.filename or "audio.wav")[-1] or ".wav"
    temp_path = f"temp_{uuid.uuid4()}{ext}"

    with open(temp_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        # ── Step 1: Transcribe + clean + extract quantity ─────────────────────
        print(f"\n🎧 /voice-transaction ← {file.filename}")

        cleaned_text, quantity = _whisper.transcribe(temp_path)

        print(f"   📝 cleaned_text : '{cleaned_text}'")
        print(f"   🔢 quantity     : {quantity}")

        if not cleaned_text:
            return _error(
                "Audio is silent or could not be transcribed. "
                "Please speak clearly and try again.",
            )

        # ── Step 2: Detect intent from cleaned tokens ─────────────────────────
        # Intent is already embedded as a canonical token ("Add"/"Remove"/"Check")
        # by the WhisperService dict/prefix-tree pipeline.
        tokens_lower = cleaned_text.lower().split()

        if "remove" in tokens_lower:
            intent = "REMOVE"
        elif "add" in tokens_lower:
            intent = "ADD"
        elif "check" in tokens_lower:
            intent = "CHECK"
        else:
            # Fallback: if no explicit action token, default to CHECK
            # so a query like "Digestive Biscuit kati?" still works
            intent = "CHECK"
            print(f"   ℹ️  No action token found — defaulting intent to CHECK")

        print(f"   🎯 Intent: {intent}")

        # ── Step 3: Validate quantity for mutating actions ────────────────────
        if intent in ("ADD", "REMOVE") and quantity <= 0:
            return _error(
                "Could not detect a quantity in the voice command. "
                "Please say a number — e.g. '10 packet Digestive Biscuit hatau'.",
                transcription=cleaned_text,
            )

        # ── Step 4: Vector search — find matching product ─────────────────────
        print(f"   🔍 Searching for: '{cleaned_text}'")

        try:
            product_id = _matcher.find_best_match(cleaned_text, db)
        except ValueError as exc:
            # No embeddings in DB — operator needs to run /refresh-embeddings
            return _error(str(exc), transcription=cleaned_text)

        if product_id is None:
            return _error(
                f"Could not confidently match the command to any product "
                f"(similarity below 90%). Please be more specific or check "
                f"that the product exists in the catalogue.",
                transcription=cleaned_text,
            )

        print(f"   🎯 product_id={product_id}")

        # ── Step 5: Execute inventory action ──────────────────────────────────
        if intent == "REMOVE":
            result = crud.deduct_inventory(
                db_session=db,
                product_id=product_id,
                quantity=quantity,
            )
            qty_changed = quantity

        elif intent == "ADD":
            result = crud.add_inventory(
                db_session=db,
                product_id=product_id,
                quantity=quantity,
            )
            qty_changed = quantity

        else:  # CHECK
            result      = crud.get_stock(db_session=db, product_id=product_id)
            qty_changed = 0

        # ── Step 6: Handle crud errors ────────────────────────────────────────
        if not result["success"]:
            return _error(result["message"], transcription=cleaned_text)

        # ── Step 7: Low-stock alert ───────────────────────────────────────────
        LOW_STOCK_THRESHOLD = 40
        alert_message       = None

        new_stock = result.get("new_stock") or result.get("current_stock", 0)
        if new_stock < LOW_STOCK_THRESHOLD:
            alert_message = (
                f"⚠️ LOW STOCK: '{result['name_english']}' is at "
                f"{new_stock} {result['unit']} "
                f"(threshold: {LOW_STOCK_THRESHOLD})."
            )
            print(f"   {alert_message}")

        # ── Step 8: Success response ──────────────────────────────────────────
        return {
            "status":        "success",
            "transcription": cleaned_text,
            "intent":        intent,
            "item":          result["name_english"],
            "item_nepali":   result.get("name_nepali", ""),
            "qty_changed":   qty_changed,
            "new_stock":     new_stock,
            "unit":          result["unit"],
            "message":       result["message"],
            "alert_message": alert_message,
        }

    except Exception as exc:
        import traceback
        print(f"❌ Unhandled error in /voice-transaction: {exc}")
        traceback.print_exc()
        return _error(f"Unexpected server error: {exc}")

    finally:
        # Always clean up the temp audio file — even on unhandled exceptions
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _error(message: str, **extra) -> dict:
    """
    Standard error envelope.

    Usage:
        return _error("Stock too low.", transcription=cleaned_text)
    Produces:
        {"status": "error", "message": "Stock too low.", "transcription": "..."}
    """
    return {"status": "error", "message": message, **extra}