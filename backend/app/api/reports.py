from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.db.session import get_db
from app.db.models import TransactionHistory, Product   # <-- added Product
from app.core.pdf_service import generate_sales_pdf

router = APIRouter()

@router.get("/sales-pdf")
def download_sales_report(days: int = 7, db: Session = Depends(get_db)):
    if days not in [1, 7, 28, 30]:
        raise HTTPException(status_code=400, detail="Invalid duration. Choose 1, 7, 28, or 30 days.")

    target_date = datetime.now() - timedelta(days=days)

    valid_actions = ["REMOVE", "DEDUCT", "SALE"]

    # Join with Product to get cost_price and selling_price
    results = (
        db.query(TransactionHistory, Product.cost_price, Product.selling_price)
        .join(Product, TransactionHistory.product_id == Product.id)
        .filter(
            func.upper(TransactionHistory.action_type).in_(valid_actions),
            TransactionHistory.timestamp >= target_date
        )
        .order_by(TransactionHistory.timestamp.desc())
        .all()
    )

    if not results:
        print(f"DEBUG: Searched for {valid_actions} after {target_date}. Found 0.")
        raise HTTPException(status_code=404, detail=f"No sales or removals found in the last {days} days.")

    pdf_bytes = generate_sales_pdf(results, days)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="SmartBiz_Sales_Report_{days}days.pdf"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.get("/sales-data")
def get_sales_data(days: int = 7, db: Session = Depends(get_db)):
    if days not in [1, 7, 14, 28, 30]:
        days = 7

    target_date = datetime.now() - timedelta(days=days)
    previous_period_date = target_date - timedelta(days=days)
    valid_actions = ["REMOVE", "DEDUCT", "SALE"]

    # Current period stats
    current_results = (
        db.query(TransactionHistory, Product.cost_price, Product.selling_price)
        .join(Product, TransactionHistory.product_id == Product.id)
        .filter(
            func.upper(TransactionHistory.action_type).in_(valid_actions),
            TransactionHistory.timestamp >= target_date
        )
        .order_by(TransactionHistory.timestamp.desc())
        .all()
    )

    # Previous period stats for % change
    prev_results = (
        db.query(TransactionHistory, Product.cost_price, Product.selling_price)
        .join(Product, TransactionHistory.product_id == Product.id)
        .filter(
            func.upper(TransactionHistory.action_type).in_(valid_actions),
            TransactionHistory.timestamp >= previous_period_date,
            TransactionHistory.timestamp < target_date
        )
        .all()
    )

    def calculate_metrics(results):
        revenue = 0.0
        profit = 0.0
        for tx, cp, sp in results:
            qty = tx.quantity_changed or 0
            sale_p = sp or 0
            cost_p = cp or 0
            revenue += sale_p * qty
            profit += (sale_p - cost_p) * qty
        return revenue, profit

    curr_revenue, curr_profit = calculate_metrics(current_results)
    prev_revenue, prev_profit = calculate_metrics(prev_results)

    def calc_change(curr, prev):
        if prev == 0:
            return 100 if curr > 0 else 0
        return round(((curr - prev) / prev) * 100)

    revenue_change = calc_change(curr_revenue, prev_revenue)
    profit_change = calc_change(curr_profit, prev_profit)

    items = []
    # Fetch recent items for display (up to 20)
    for tx, cp, sp in current_results[:20]:
        items.append({
            "id": str(tx.id),
            "name": tx.product_name_english or "Unknown",
            "category": "GROCERIES", # mock category for now
            "costPrice": cp or 0.0,
            "salePrice": sp or 0.0,
            "status": "Paid",
            "date": tx.timestamp.isoformat()
        })

    # Return structure expected by the frontend
    return {
        "stats": {
            "profit": round(curr_profit),
            "revenue": round(curr_revenue),
            "profitChange": profit_change,
            "revenueChange": revenue_change,
        },
        "items": items
    }