"""
chatbot.py
==========
SmartBiz AI — Chatbot API Routes

Handles all chat interactions:
  - Quick action buttons (low_stock, today_sales, summary, top_products, restock_advice)
  - Free-text questions with full inventory + transaction context
  - Conversation history for multi-turn dialogue

All routes build rich context from the live database, then pass it
to ai_service.get_ai_advice() which calls Qwen 2.5 7B via Ollama.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date, datetime, timedelta

from app.db.session import get_db
from app.db.models import Product, TransactionHistory
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.core.ai_service import get_ai_advice


router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# HELPER — Build inventory snapshot string
# ══════════════════════════════════════════════════════════════════════════════

def _build_inventory_snapshot(db: Session) -> str:
    """Return a formatted string of all products with stock levels."""
    products = db.query(Product).order_by(Product.name_english).all()

    if not products:
        return "No products found in inventory."

    lines = ["Current Inventory (all products):"]
    for p in products:
        stock = p.current_stock or 0
        status = ""
        if stock <= 0:
            status = " [OUT OF STOCK ❌]"
        elif stock < 10:
            status = " [CRITICALLY LOW 🚨]"
        elif stock < 40:
            status = " [LOW ⚠️]"

        lines.append(
            f"  • {p.name_english} ({p.name_nepali}): "
            f"{stock:.0f} {p.unit}{status}"
        )

    total_stock = sum(p.current_stock or 0 for p in products)
    lines.append(f"\nTotal Products: {len(products)}")
    lines.append(f"Total Physical Units: {total_stock:.0f}")

    return "\n".join(lines)


def _build_recent_transactions(db: Session, days: int = 7, limit: int = 30) -> str:
    """Return a formatted string of recent transactions."""
    since = datetime.utcnow() - timedelta(days=days)

    txns = (
        db.query(TransactionHistory)
        .filter(TransactionHistory.timestamp >= since)
        .order_by(desc(TransactionHistory.timestamp))
        .limit(limit)
        .all()
    )

    if not txns:
        return f"No transactions recorded in the last {days} days."

    lines = [f"Recent Transactions (last {days} days, up to {limit} shown):"]
    for t in txns:
        ts = t.timestamp.strftime("%Y-%m-%d %H:%M") if t.timestamp else "unknown"
        lines.append(
            f"  • [{ts}] {t.action_type} {t.quantity_changed:.0f} {t.unit} "
            f"of {t.product_name_english} → stock after: {t.stock_after_transaction:.0f}"
        )

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CHAT ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Main chatbot endpoint. Accepts either:
      - A quick action button press (request.action)
      - A free-text message (request.message)
      - Optional conversation history (request.history)

    Returns the AI's response with status.
    """

    context_data = ""
    user_intent = request.message or ""

    # Extract conversation history for context
    history = None
    if request.history:
        history = [{"role": m.role, "text": m.text} for m in request.history]

    # ─── ACTION 1: LOW STOCK ALERT ───────────────────────────────────────────
    if request.action == "low_stock":
        low_items = (
            db.query(Product)
            .filter(Product.current_stock < 40)
            .order_by(Product.current_stock)
            .all()
        )

        if not low_items:
            context_data = "All items have sufficient stock (40 or more units). No items are low."
        else:
            critical = [p for p in low_items if (p.current_stock or 0) < 10]
            warning = [p for p in low_items if 10 <= (p.current_stock or 0) < 40]

            lines = []
            if critical:
                lines.append("CRITICALLY LOW STOCK (under 10 units):")
                for p in critical:
                    lines.append(
                        f"  🚨 {p.name_english} ({p.name_nepali}): "
                        f"{p.current_stock:.0f} {p.unit}"
                    )

            if warning:
                lines.append("\nLOW STOCK (under 40 units):")
                for p in warning:
                    lines.append(
                        f"  ⚠️ {p.name_english} ({p.name_nepali}): "
                        f"{p.current_stock:.0f} {p.unit}"
                    )

            context_data = "\n".join(lines)

        user_intent = (
            "Analyze the low stock items. For each critically low item, "
            "explain why it's urgent. Prioritize what to restock first based on "
            "which items are most essential for a Nepali grocery store. "
            "Give specific quantity recommendations."
        )

    # ─── ACTION 2: TODAY'S SALES ─────────────────────────────────────────────
    elif request.action == "today_sales":
        today = date.today()
        sales = (
            db.query(TransactionHistory)
            .filter(
                TransactionHistory.action_type.in_(["REMOVE", "remove", "DEDUCT", "SALE"]),
                TransactionHistory.timestamp >= datetime(today.year, today.month, today.day),
            )
            .order_by(desc(TransactionHistory.timestamp))
            .all()
        )

        additions = (
            db.query(TransactionHistory)
            .filter(
                TransactionHistory.action_type.in_(["ADD", "add"]),
                TransactionHistory.timestamp >= datetime(today.year, today.month, today.day),
            )
            .all()
        )

        lines = []
        if not sales:
            lines.append("No sales/deductions recorded today.")
        else:
            lines.append(f"Today's Sales ({len(sales)} transactions):")
            # Aggregate by product
            product_totals: dict[str, float] = {}
            for s in sales:
                key = f"{s.product_name_english} ({s.unit})"
                product_totals[key] = product_totals.get(key, 0) + (s.quantity_changed or 0)

            for prod, total in sorted(product_totals.items(), key=lambda x: -x[1]):
                lines.append(f"  💰 {prod}: {total:.0f} sold")

            lines.append(f"\nTotal sale transactions: {len(sales)}")

        if additions:
            lines.append(f"\nToday's Stock Additions ({len(additions)} transactions):")
            for a in additions:
                lines.append(
                    f"  📦 {a.product_name_english}: +{a.quantity_changed:.0f} {a.unit}"
                )

        context_data = "\n".join(lines)
        user_intent = (
            "Summarize today's sales activity. Identify the best-selling item. "
            "If there are no sales, give encouraging advice on how to boost sales today. "
            "Be concise and motivating."
        )

    # ─── ACTION 3: BUSINESS SUMMARY ──────────────────────────────────────────
    elif request.action == "summary":
        # Full inventory snapshot
        all_products = db.query(Product).all()
        total_products = len(all_products)
        total_stock = sum(p.current_stock or 0 for p in all_products)
        low_count = sum(1 for p in all_products if (p.current_stock or 0) < 40)
        critical_count = sum(1 for p in all_products if (p.current_stock or 0) < 10)

        # Recent transaction stats
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_sales = (
            db.query(func.count(TransactionHistory.id))
            .filter(
                TransactionHistory.action_type.in_(["REMOVE", "remove", "DEDUCT", "SALE"]),
                TransactionHistory.timestamp >= week_ago,
            )
            .scalar() or 0
        )
        week_additions = (
            db.query(func.count(TransactionHistory.id))
            .filter(
                TransactionHistory.action_type.in_(["ADD", "add"]),
                TransactionHistory.timestamp >= week_ago,
            )
            .scalar() or 0
        )

        context_data = (
            f"BUSINESS OVERVIEW:\n"
            f"  Total Unique Products: {total_products}\n"
            f"  Total Physical Units in Store: {total_stock:.0f}\n"
            f"  Low Stock Items (< 40 units): {low_count}\n"
            f"  Critically Low (< 10 units): {critical_count}\n"
            f"\nWEEKLY ACTIVITY (last 7 days):\n"
            f"  Sale/Removal Transactions: {week_sales}\n"
            f"  Stock Addition Transactions: {week_additions}\n"
        )

        user_intent = (
            "Give a professional 3-4 sentence business health summary. "
            "Highlight what's going well and what needs attention. "
            "End with one specific actionable recommendation."
        )

    # ─── ACTION 4: TOP PRODUCTS ──────────────────────────────────────────────
    elif request.action == "top_products":
        month_ago = datetime.utcnow() - timedelta(days=30)

        # Get top sold products in last 30 days
        top_sold = (
            db.query(
                TransactionHistory.product_name_english,
                TransactionHistory.unit,
                func.sum(TransactionHistory.quantity_changed).label("total_qty"),
                func.count(TransactionHistory.id).label("txn_count"),
            )
            .filter(
                TransactionHistory.action_type.in_(["REMOVE", "remove", "DEDUCT", "SALE"]),
                TransactionHistory.timestamp >= month_ago,
            )
            .group_by(TransactionHistory.product_name_english, TransactionHistory.unit)
            .order_by(desc("total_qty"))
            .limit(10)
            .all()
        )

        if not top_sold:
            context_data = "No sales data available in the last 30 days."
        else:
            lines = ["Top Sold Products (last 30 days):"]
            for i, row in enumerate(top_sold, 1):
                lines.append(
                    f"  {i}. {row.product_name_english}: "
                    f"{row.total_qty:.0f} {row.unit} sold "
                    f"({row.txn_count} transactions)"
                )
            context_data = "\n".join(lines)

        user_intent = (
            "Analyze the top-selling products. Identify which products are "
            "star performers and why. Suggest which products to promote more "
            "and which to ensure are always well-stocked."
        )

    # ─── ACTION 5: RESTOCK ADVICE ────────────────────────────────────────────
    elif request.action == "restock_advice":
        # Get current inventory + recent sales velocity
        products = db.query(Product).all()
        week_ago = datetime.utcnow() - timedelta(days=7)

        lines = ["RESTOCK ANALYSIS:"]
        for p in products:
            # Calculate weekly sales velocity
            weekly_sold = (
                db.query(func.sum(TransactionHistory.quantity_changed))
                .filter(
                    TransactionHistory.product_id == p.id,
                    TransactionHistory.action_type.in_(["REMOVE", "remove", "DEDUCT", "SALE"]),
                    TransactionHistory.timestamp >= week_ago,
                )
                .scalar() or 0
            )

            stock = p.current_stock or 0
            days_left = (stock / (weekly_sold / 7)) if weekly_sold > 0 else 999

            lines.append(
                f"  • {p.name_english} ({p.name_nepali}):\n"
                f"    Current Stock: {stock:.0f} {p.unit}\n"
                f"    Weekly Sales: {weekly_sold:.0f} {p.unit}\n"
                f"    Estimated Days Until Stockout: {days_left:.0f}"
            )

        context_data = "\n".join(lines)
        user_intent = (
            "Based on the current stock levels and weekly sales velocity, "
            "create a priority restocking list. For each item that needs restocking, "
            "suggest how much to order (enough for 2 weeks of sales). "
            "Order them by urgency (items that will run out soonest first)."
        )

    # ─── ACTION 6: FREE TEXT QUESTION ────────────────────────────────────────
    else:
        if not request.message:
            raise HTTPException(
                status_code=400,
                detail="Must provide either a 'message' or an 'action'.",
            )

        # For free-text questions, provide full context so AI can answer anything
        inventory_snapshot = _build_inventory_snapshot(db)
        recent_txns = _build_recent_transactions(db, days=7, limit=20)

        context_data = f"{inventory_snapshot}\n\n{recent_txns}"

    # ─── GENERATE AI RESPONSE ────────────────────────────────────────────────
    ai_reply = await get_ai_advice(context_data, user_intent, history)

    return ChatResponse(status="success", reply=ai_reply)