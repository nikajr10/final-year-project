from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import Product, VoiceLog
from app.core.whisper_service import WhisperService
from app.core.llm_service import LLMService
from sentence_transformers import SentenceTransformer
from app.api import auth
import shutil
import os
import uuid

# Initialize the App
app = FastAPI(title="SmartBiz AI Backend")
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

# --- INITIALIZATION ---
print("⏳ Loading AI Models...")
print("   - Whisper (Ears)...")
whisper_service = WhisperService()

print("   - Llama 3 (Brain)...")
llm_service = LLMService()

print("   - SBERT (Vector Math)...")
vector_model = SentenceTransformer('all-MiniLM-L6-v2')

print("✅ All AI Systems Ready!")


@app.post("/process-voice")
async def process_voice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Step 1: Audio Processing (FFmpeg/VAD - handled in WhisperService)
    Step 2: Speech-to-Text (Whisper)
    Step 3: Intent Extraction (Llama 3)
    Step 4: Text-to-Vector (SBERT)
    Step 5: Fuzzy Matching / Vector Search (pgvector)
    Step 6: Database Update (Postgres)
    """
    
    # --- 1. SAVE TEMP FILE ---
    temp_filename = f"temp_{uuid.uuid4()}.wav"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # --- 2. TRANSCRIBE (Whisper) ---
        print(f"\n🎧 Processing Audio: {file.filename}")
        transcription_result = whisper_service.model.transcribe(temp_filename, language='ne', fp16=False)
        nepali_text = transcription_result['text'].strip()
        print(f"🗣️ User said: '{nepali_text}'")

        # --- 3. INTELLIGENCE (Llama 3) ---
        # Expected: {'intent': 'ADD', 'item': 'Namak', 'qty': 5, 'unit': 'packet'}
        ai_data = llm_service.process_text(nepali_text)
        
        if not ai_data or 'item' not in ai_data:
            return {"status": "error", "message": "Could not understand item", "transcription": nepali_text}

        candidate_item = ai_data['item'] # e.g., "Namak" or "Salt"
        qty = float(ai_data['qty'])
        intent = ai_data['intent']

        print(f"🧠 Llama Extracted: {candidate_item} ({intent} {qty})")

        # --- 4 & 5. SEARCH STRATEGY ---
        
        # Strategy A: Exact Match (Fastest)
        product = db.query(Product).filter(Product.name_nepali == candidate_item).first()

        match_type = "Exact Match"

        # Strategy B: Vector Search (The Safety Net)
        if not product:
            print(f"⚠️ Exact match failed for '{candidate_item}'. Activating Vector Search...")
            
            query_vector = vector_model.encode(candidate_item).tolist()

            product = db.scalars(
                select(Product)
                .order_by(Product.embedding.cosine_distance(query_vector))
                .limit(1)
            ).first()

            if product:
                print(f"✅ Vector Search found: '{product.name_nepali}' (English: {product.name_english})")
                match_type = "Vector Fuzzy Match"
            else:
                return {"status": "error", "message": "Item not found even with AI Search."}

        # --- 6. DATABASE UPDATE & LOGIC ROUTING ---
        if intent == "ADD":
            product.current_stock += qty
            action_msg = "Added to stock"
        elif intent == "REMOVE":
            product.current_stock -= qty
            action_msg = "Removed from stock"
        elif intent == "CHECK":
            # For a CHECK command, we don't modify the database stock.
            # We just set the message and optionally force the qty_changed to 0.
            action_msg = "Checked stock level"
            qty = 0.0  
        else:
            action_msg = "Unknown action"
            qty = 0.0
        
        # Log the transaction
        log = VoiceLog(
            original_text=nepali_text,
            corrected_intent=f"{intent} {qty} {product.name_nepali}",
            confidence_score=1.0 if match_type == "Exact Match" else 0.85
        )
        db.add(log)
        db.commit()
        db.refresh(product)

        # --- 7. THRESHOLD ALERT LOGIC ---
        alert_message = None
        if product.current_stock < 40:
            alert_message = f"⚠️ CRITICAL: {product.name_english} stock has dropped to {product.current_stock} {product.unit}! (Threshold: 40)"
            print(f"🚨 {alert_message}")

        # --- FINAL RESPONSE ---
        return {
            "status": "success",
            "transcription": nepali_text,
            "match_method": match_type,
            "action": action_msg,
            "item": product.name_english,
            "item_nepali": product.name_nepali,
            "qty_changed": qty,
            "new_stock": product.current_stock,
            "unit": product.unit,
            "alert_message": alert_message
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}
    
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)