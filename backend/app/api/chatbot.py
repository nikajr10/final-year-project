from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.db.session import get_db
from app.db.models import Product, TransactionHistory
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.core.ai_service import get_ai_advice

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest, db: Session = Depends(get_db)):
    context_data = ""
    user_intent = request.message or ""

    # ─── ACTION 1: LOW STOCK FAQ ─────────────────────────────────────────────
    if request.action == "low_stock":
        low_items = db.query(Product).filter(Product.current_stock < 10).all()
        
        if not low_items:
            context_data = "All items have sufficient stock (10 or more units)."
        else:
            context_data = "Low Stock Items:\n" + "\n".join(
                [f"- {p.name_english} ({p.name_nepali}): {p.current_stock} {p.unit}" for p in low_items]
            )
        user_intent = "Summarize the low stock items clearly and advise me on what to restock most urgently."

    # ─── ACTION 2: TODAY'S SALES FAQ ─────────────────────────────────────────
    elif request.action == "today_sales":
        today = date.today()
        # Fetching all removals/deductions for today
        sales = db.query(TransactionHistory).filter(
            TransactionHistory.action_type.in_(["REMOVE", "remove", "DEDUCT", "SALE"]),
            TransactionHistory.timestamp >= today
        ).all()
        
        if not sales:
            context_data = "No sales or deductions recorded today."
        else:
            context_data = "Today's Sales:\n" + "\n".join(
                [f"- {s.product_name_english}: {s.quantity_changed} {s.unit} sold" for s in sales]
            )
        user_intent = "Summarize today's sales. Point out the best-selling item and congratulate the user."

    # ─── ACTION 3: BUSINESS SUMMARY FAQ ──────────────────────────────────────
    elif request.action == "summary":
        total_products = db.query(Product).count()
        
        # Calculate total physical stock (safely handle None values)
        all_products = db.query(Product.current_stock).all()
        total_stock = sum([p.current_stock for p in all_products if p.current_stock])
        
        context_data = f"Total Unique Products in System: {total_products}\nTotal Physical Units in Store: {total_stock}"
        user_intent = "Give a brief, 2-sentence encouraging summary of the business health. Make it sound professional."

    # ─── ACTION 4: FREE TEXT QUESTION ────────────────────────────────────────
    else:
        if not request.message:
            raise HTTPException(status_code=400, detail="Must provide either a 'message' or an 'action'.")
        
        # For general questions, we provide a snapshot of the top 20 items so the AI has context
        top_items = db.query(Product).limit(20).all()
        context_data = "Current Inventory Snapshot (Top 20 items):\n" + "\n".join(
            [f"- {p.name_english}: {p.current_stock} {p.unit}" for p in top_items]
        )

    # ─── GENERATE AI RESPONSE ────────────────────────────────────────────────
    # Wait for the M2 Pro / Ollama to process the data
    ai_reply = await get_ai_advice(context_data, user_intent)

    return ChatResponse(status="success", reply=ai_reply)