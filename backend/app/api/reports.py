from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.session import get_db
from app.db.models import TransactionHistory
from app.core.pdf_service import generate_sales_pdf

router = APIRouter()

@router.get("/sales-pdf")
def download_sales_report(days: int = 7, db: Session = Depends(get_db)):
    if days not in [1, 7, 28]:
        raise HTTPException(status_code=400, detail="Invalid duration. Choose 1, 7, or 28 days.")
        
    target_date = datetime.utcnow() - timedelta(days=days)
    
    # Clean, perfect query hitting the ledger instead of parsing text
    logs = db.query(TransactionHistory).filter(
        TransactionHistory.action_type == "REMOVE",
        TransactionHistory.timestamp >= target_date
    ).order_by(TransactionHistory.timestamp.desc()).all()
    
    if not logs:
        raise HTTPException(status_code=404, detail=f"No sales or removals found in the last {days} days.")
        
    pdf_bytes = generate_sales_pdf(logs, days)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=SmartBiz_Sales_Report_{days}days.pdf"
        }
    )