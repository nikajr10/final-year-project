from fpdf import FPDF
from datetime import datetime

def generate_sales_pdf(logs, days: int) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    
    # --- Title ---
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"SmartBiz Sales & Removal Report (Last {days} Days)", ln=True, align='C')
    pdf.ln(10)
    
    # --- Table Headers ---
    pdf.set_font("Arial", 'B', 10) # Slightly smaller font to fit 5 columns nicely
    
    # Total A4 width is ~190mm. Let's divide it perfectly:
    # 35 + 55 + 30 + 35 + 35 = 190mm
    pdf.cell(35, 10, "Date & Time", border=1, align='C')
    pdf.cell(55, 10, "Item", border=1, align='C')
    pdf.cell(30, 10, "Action", border=1, align='C')
    pdf.cell(35, 10, "Quantity", border=1, align='C')
    pdf.cell(35, 10, "Stock", border=1, align='C')
    pdf.ln()
    
    # --- Table Data ---
    pdf.set_font("Arial", '', 10)
    
    for log in logs:
        # 1. Date
        date_str = log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "N/A"
        
        # 2. Item Name (English only)
        item_name = str(getattr(log, 'product_name_english', 'Unknown'))
        
        # 3. Action
        action = str(getattr(log, 'action_type', 'N/A'))
        
        # 4. Quantity formatting
        qty_val = getattr(log, 'quantity_changed', 0)
        unit_val = getattr(log, 'unit', '')
        
        if isinstance(qty_val, float) and qty_val.is_integer():
            qty_val = int(qty_val)
        qty_str = f"{qty_val} {unit_val}".strip()

        # 5. New Stock (Remaining amount) formatting
        stock_val = getattr(log, 'stock_after_transaction', 0)
        
        if isinstance(stock_val, float) and stock_val.is_integer():
            stock_val = int(stock_val)
        stock_str = f"{stock_val} {unit_val}".strip()
        
        # Write row to PDF
        pdf.cell(35, 10, date_str, border=1)
        pdf.cell(55, 10, item_name, border=1)
        pdf.cell(30, 10, action, border=1, align='C')
        pdf.cell(35, 10, qty_str, border=1, align='C')
        pdf.cell(35, 10, stock_str, border=1, align='C')
        pdf.ln()

    # Output to string and encode to bytes for FastAPI
    pdf_string = pdf.output(dest='S')
    
    return pdf_string.encode('latin-1')