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