from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.session import get_db
from app.db.models import TransactionHistory
from app.core.pdf_service import generate_sales_pdf

router = APIRouter()

@router.get("/sales-pdf")
def download_sales_report(days: int = 7, db: Session = Depends(get_db)):
    # Added 30 just in case your frontend accidentally sends 30 instead of 28
    if days not in [1, 7, 28, 30]: 
        raise HTTPException(status_code=400, detail="Invalid duration. Choose 1, 7, or 28 days.")
        
    # Using local now() is often safer than utcnow() if your database relies on local server time
    target_date = datetime.now() - timedelta(days=days)
    
    # FIX 1: Catch all possible terms for a deduction/sale
    # This prevents the 404 error if your DB saves "DEDUCT" or lowercase "remove"
    valid_actions = ["REMOVE", "remove", "DEDUCT", "deduct", "SALE", "sale"]
    
    logs = db.query(TransactionHistory).filter(
        TransactionHistory.action_type.in_(valid_actions),
        TransactionHistory.timestamp >= target_date
    ).order_by(TransactionHistory.timestamp.desc()).all()
    
    if not logs:
        # Prints to your Uvicorn terminal so you can verify the date calculation
        print(f"DEBUG: Searched for {valid_actions} after {target_date}. Found 0.")
        raise HTTPException(status_code=404, detail=f"No sales or removals found in the last {days} days.")
        
    pdf_bytes = generate_sales_pdf(logs, days)
    
    # FIX 2: Added Access-Control-Expose-Headers
    # This ensures your frontend is allowed to read the attachment and trigger the download prompt
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="SmartBiz_Sales_Report_{days}days.pdf"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )