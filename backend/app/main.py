"""
main.py — SmartBiz AI FastAPI Entry Point
"""

import os
import uuid
import shutil
import numpy as np
from difflib import SequenceMatcher
from app.api import routes as voice_routes

from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from app.api import chatbot

from app.db.session import get_db
from app.db.models import Product, VoiceLog, TransactionHistory
from app.core.whisper_service import WhisperService
from app.core.llm_service import LLMService
from app.api import auth, reports
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmartBiz AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/auth",      tags=["Authentication"])
app.include_router(reports.router,      prefix="/api/reports",   tags=["Reports"])
app.include_router(chatbot.router,      prefix="/api/chat",      tags=["AI Chatbot"])
app.include_router(voice_routes.router, prefix="/api/inventory", tags=["Voice Inventory"])

print("⏳ Loading AI Models...")
print("   - Whisper (Ears)...")
whisper_service = WhisperService()
print("   - Llama 3 (Brain)...")
llm_service = LLMService()
print("   - SBERT (Vector Engine)...")
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ All AI Systems Ready!")


def _find_product(candidate_item: str, db: Session) -> tuple["Product | None", str]:
    product = db.query(Product).filter(Product.name_nepali == candidate_item).first()
    if product:
        print(f"   ✅ Tier 1 (name_nepali exact): {product.name_english}")
        return product, "Exact Match"

    product = db.query(Product).filter(Product.name_english == candidate_item).first()
    if product:
        print(f"   ✅ Tier 1 (name_english exact): {product.name_english}")
        return product, "Exact Match"

    print(f"⚠️  No exact match for '{candidate_item}' — running HNSW vector search...")
    try:
        query_vector = sbert_model.encode(candidate_item).tolist()
        result = db.scalars(
            select(Product)
            .filter(Product.embedding.isnot(None))
            .order_by(Product.embedding.cosine_distance(query_vector))
            .limit(1)
        ).first()

        if result:
            distance = float(
                db.execute(
                    select(Product.embedding.cosine_distance(query_vector))
                    .where(Product.id == result.id)
                ).scalar()
            )
            COSINE_THRESHOLD = 0.6
            print(f"   🤖 HNSW best: '{result.name_english}' (cosine_distance={distance:.4f})")
            if distance < COSINE_THRESHOLD:
                print(f"   ✅ Tier 2 (HNSW vector): {result.name_english}")
                return result, "HNSW Vector Match"
            else:
                print(f"   ⚠️  Score {distance:.4f} exceeds threshold — rejected.")
    except Exception as e:
        print(f"   ❌ HNSW error: {e}")

    print(f"⚠️  Running fuzzy string match...")
    products   = db.query(Product).all()
    best       = None
    best_ratio = 0.0
    for p in products:
        for name in [p.name_english, p.name_nepali]:
            ratio = SequenceMatcher(None, candidate_item.lower(), name.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best       = p

    print(f"   🔤 Fuzzy best: '{best.name_english if best else None}' (ratio={best_ratio:.3f})")
    if best and best_ratio >= 0.4:
        print(f"   ✅ Tier 3 (fuzzy string): {best.name_english}")
        return best, "Fuzzy String Match"

    return None, "Not Found"


def _format_qty(qty: float) -> "int | float":
    return int(qty) if qty == int(qty) else qty


@app.post("/process-voice")
async def process_voice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext       = os.path.splitext(file.filename)[-1] or ".wav"
    temp_path = f"temp_{uuid.uuid4()}{ext}"

    with open(temp_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        print(f"\n🎧 Processing: {file.filename}")
        transcribe_result = whisper_service.transcribe(temp_path)
        cleaned_text = transcribe_result[0] if isinstance(transcribe_result, tuple) else transcribe_result
        print(f"🗣️  Cleaned: '{cleaned_text}'")

        if not cleaned_text:
            return {"status": "error", "message": "Audio is silent or could not be transcribed."}

        ai_data = llm_service.process_text(cleaned_text)
        if not ai_data or "item" not in ai_data:
            return {"status": "error", "message": "Could not understand the voice command.", "transcription": cleaned_text}

        candidate_item = ai_data["item"]
        intent         = ai_data["intent"]
        qty            = float(ai_data["qty"])
        unit_hint      = ai_data.get("unit", "")

        print(f"🧠 Parsed: item='{candidate_item}'  intent={intent}  qty={qty}  unit={unit_hint}")

        product, match_type = _find_product(candidate_item, db)
        if not product:
            return {"status": "error", "message": f"'{candidate_item}' not found in inventory.", "transcription": cleaned_text}

        if intent == "ADD":
            product.current_stock += qty
            action_msg = "Added to stock"
        elif intent == "REMOVE":
            if product.current_stock < qty:
                return {
                    "status": "error",
                    "message": f"Cannot remove {_format_qty(qty)} {product.unit} of {product.name_english} — only {_format_qty(product.current_stock)} in stock.",
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

        db.add(VoiceLog(
            original_text    = cleaned_text,
            corrected_intent = f"{intent} {_format_qty(qty)} {product.name_nepali}",
            confidence_score = 1.0 if match_type == "Exact Match" else 0.85,
        ))

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

        LOW_STOCK_THRESHOLD = 40
        alert_message = None
        if product.current_stock < LOW_STOCK_THRESHOLD:
            alert_message = (
                f"⚠️ LOW STOCK: {product.name_english} is at "
                f"{_format_qty(product.current_stock)} {product.unit} "
                f"(threshold: {LOW_STOCK_THRESHOLD})"
            )

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


@app.post("/refresh-embeddings")
async def refresh_embeddings(db: Session = Depends(get_db)):
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
    return {"status": "success", "message": f"Embeddings refreshed for {len(products)} products."}


@app.get("/stock")
async def get_all_stock(db: Session = Depends(get_db)):
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