from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, time
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
        qty = float(tx.quantity_changed or 0)
        cost_price = float(cp or 0.0)
        selling_price = float(sp or 0.0)

        items.append({
            "id": str(tx.id),
            "name": tx.product_name_english or "Unknown",
            "category": "GROCERIES", # mock category for now
            "costPrice": cost_price,
            "salePrice": cost_price * qty,
            "sellingPrice": selling_price,
            "quantity": qty,
            "unit": tx.unit or "",
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

@router.get("/profit-series")
def get_profit_series(days: int = 7, db: Session = Depends(get_db)):
    if days not in [7, 14, 28, 30]:
        days = 7

    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)
    start_datetime = datetime.combine(start_date, time.min)
    valid_actions = ["REMOVE", "DEDUCT", "SALE"]

    results = (
        db.query(TransactionHistory, Product.cost_price, Product.selling_price)
        .join(Product, TransactionHistory.product_id == Product.id)
        .filter(
            func.upper(TransactionHistory.action_type).in_(valid_actions),
            TransactionHistory.timestamp >= start_datetime
        )
        .order_by(TransactionHistory.timestamp.asc())
        .all()
    )

    daily_profit = {
        start_date + timedelta(days=offset): 0.0
        for offset in range(days)
    }

    for tx, cp, sp in results:
        tx_date = tx.timestamp.date()
        if tx_date not in daily_profit:
            continue

        qty = tx.quantity_changed or 0
        cost_price = cp or 0
        selling_price = sp or 0
        daily_profit[tx_date] += (selling_price - cost_price) * qty

    ordered_dates = sorted(daily_profit.keys())
    series = [
        {
            "date": day.isoformat(),
            "label": day.strftime("%a"),
            "value": round(daily_profit[day], 2),
        }
        for day in ordered_dates
    ]

    total_profit = round(sum(point["value"] for point in series), 2)
    average_profit = round(total_profit / days, 2) if days else 0

    return {
        "days": days,
        "series": series,
        "summary": {
            "totalProfit": total_profit,
            "averageDailyProfit": average_profit,
        },
    }

@router.get("/product-series")
def get_product_series(
    days: int = 7,
    product_id: int | None = None,
    db: Session = Depends(get_db),
):
    if days not in [7, 14, 28, 30]:
        days = 7

    products = (
        db.query(Product)
        .order_by(func.lower(Product.name_english).asc())
        .all()
    )

    if not products:
        return {
            "days": days,
            "products": [],
            "selectedProduct": None,
            "series": [],
        }

    selected_product = next((product for product in products if product.id == product_id), products[0])
    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)
    start_datetime = datetime.combine(start_date, time.min)
    valid_actions = ["REMOVE", "DEDUCT", "SALE"]

    results = (
        db.query(TransactionHistory)
        .filter(
            TransactionHistory.product_id == selected_product.id,
            func.upper(TransactionHistory.action_type).in_(valid_actions + ["ADD"]),
            TransactionHistory.timestamp >= start_datetime,
        )
        .order_by(TransactionHistory.timestamp.asc())
        .all()
    )

    daily_net_changes = {
        start_date + timedelta(days=offset): 0.0
        for offset in range(days)
    }

    for tx in results:
        tx_date = tx.timestamp.date()
        if tx_date not in daily_net_changes:
            continue

        qty = float(tx.quantity_changed or 0.0)
        action = (tx.action_type or "").upper()

        if action == "ADD":
            daily_net_changes[tx_date] += qty
        elif action in valid_actions:
            daily_net_changes[tx_date] -= qty

    closing_stock_by_day = {}
    running_stock = float(selected_product.current_stock or 0.0)
    current_day = today
    closing_stock_by_day[current_day] = running_stock

    while current_day > start_date:
        running_stock -= daily_net_changes[current_day]
        current_day = current_day - timedelta(days=1)
        closing_stock_by_day[current_day] = running_stock

    ordered_dates = sorted(closing_stock_by_day.keys())
    series = [
        {
            "date": day.isoformat(),
            "label": day.strftime("%a"),
            "value": round(closing_stock_by_day[day], 2),
        }
        for day in ordered_dates
    ]

    return {
        "days": days,
        "products": [
            {
                "id": product.id,
                "name": product.name_english,
                "nameNepali": product.name_nepali,
                "unit": product.unit,
                "currentStock": round(product.current_stock or 0.0, 2),
            }
            for product in products
        ],
        "selectedProduct": {
            "id": selected_product.id,
            "name": selected_product.name_english,
            "nameNepali": selected_product.name_nepali,
            "unit": selected_product.unit,
            "currentStock": round(selected_product.current_stock or 0.0, 2),
        },
        "series": series,
    }
