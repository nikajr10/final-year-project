"""
routes.py
=========
SmartBiz AI — Voice Transaction API Routes
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
from app.db.crud import InsufficientStockError, ProductNotFoundError

router = APIRouter()

print("⏳ routes.py — loading AI services...")
_whisper = WhisperService()
_matcher = VectorMatcher()
print("✅ routes.py — AI services ready.")


@router.post("/voice-transaction")
async def voice_transaction(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db),
):
    ext       = os.path.splitext(file.filename or "audio.wav")[-1] or ".wav"
    temp_path = f"temp_{uuid.uuid4()}{ext}"

    with open(temp_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        print(f"\n🎧 /voice-transaction ← {file.filename}")

        cleaned_text, quantity = _whisper.transcribe(temp_path)
        print(f"   📝 cleaned : '{cleaned_text}'")
        print(f"   🔢 qty     : {quantity}")

        if not cleaned_text:
            return _error("Audio is silent or could not be transcribed.")

        tokens_lower = cleaned_text.lower().split()
        if "remove" in tokens_lower:
            intent = "REMOVE"
        elif "add" in tokens_lower:
            intent = "ADD"
        elif "check" in tokens_lower:
            intent = "CHECK"
        else:
            intent = "CHECK"
            print("   ℹ️  No action token — defaulting to CHECK")

        print(f"   🎯 Intent: {intent}")

        if intent in ("ADD", "REMOVE") and quantity <= 0:
            return _error(
                "Could not detect a quantity. Please say a number.",
                transcription=cleaned_text,
            )

        print(f"   🔍 Searching: '{cleaned_text}'")
        try:
            product_id = _matcher.find_best_match(cleaned_text, db)
        except ValueError as exc:
            return _error(str(exc), transcription=cleaned_text)

        if product_id is None:
            return _error(
                "Item not recognized or too ambiguous. "
                "Please say 'Tiger Biscuit' or 'Digestive Biscuit' clearly.",
                transcription=cleaned_text,
            )

        print(f"   🎯 product_id={product_id}")

        try:
            if intent == "REMOVE":
                result      = crud.deduct_inventory(db, product_id, quantity)
                qty_changed = quantity
            elif intent == "ADD":
                result      = crud.add_inventory(db, product_id, quantity)
                qty_changed = quantity
            else:
                result      = crud.get_stock(db, product_id)
                qty_changed = 0

        except InsufficientStockError as exc:
            return _error(
                "Insufficient stock for this transaction.",
                detail=str(exc),
                transcription=cleaned_text,
            )
        except ProductNotFoundError as exc:
            return _error(
                "Product not found in the database.",
                detail=str(exc),
                transcription=cleaned_text,
            )

        LOW_STOCK_THRESHOLD = 40
        alert_message       = None
        new_stock = result.get("new_stock") or result.get("current_stock", 0)
        if isinstance(new_stock, (int, float)) and new_stock < LOW_STOCK_THRESHOLD:
            alert_message = (
                f"⚠️ LOW STOCK: '{result['name_english']}' is at "
                f"{new_stock} {result['unit']} (threshold: {LOW_STOCK_THRESHOLD})."
            )
            print(f"   {alert_message}")

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
        print(f"❌ Unhandled error: {exc}")
        traceback.print_exc()
        return _error(f"Unexpected server error: {exc}")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _error(message: str, **extra) -> dict:
    return {"status": "error", "message": message, **extra}