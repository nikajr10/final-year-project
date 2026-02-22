from fpdf import FPDF
from datetime import datetime

class PDFReport(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 16)
        self.cell(0, 10, "SmartBiz Inventory System", border=False, ln=True, align="C")
        self.set_font("helvetica", "I", 12)
        self.cell(0, 10, "Automated Sales & Stock Removal Report", border=False, ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_sales_pdf(logs: list, days: int) -> bytes:
    pdf = PDFReport()
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, f"Sales Report (Last {days} Days)", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(60, 10, "Date", border=1)
    pdf.cell(70, 10, "Item (Nepali)", border=1)
    pdf.cell(40, 10, "Qty Sold", border=1, ln=True)
    
    pdf.set_font("helvetica", "", 12)
    total_sold = 0.0
    
    for log in logs:
        # Pulling directly from the strict ledger columns
        qty = log.quantity_changed
        item = log.product_name_nepali
        total_sold += qty
        
        date_str = log.timestamp.strftime('%Y-%m-%d %H:%M')
        
        pdf.cell(60, 10, date_str, border=1)
        pdf.cell(70, 10, item, border=1)
        pdf.cell(40, 10, f"{qty} {log.unit}", border=1, ln=True)
        
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Total Units Sold/Removed: {total_sold}", ln=True)
    
    return bytes(pdf.output())