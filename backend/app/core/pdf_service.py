from fpdf import FPDF
from datetime import datetime

def generate_sales_pdf(results, days: int) -> bytes:
    pdf = FPDF(orientation='L', unit='mm', format='A4')  # Landscape for extra columns
    pdf.add_page()

    # --- Title ---
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"SmartBiz Sales & Removal Report (Last {days} Days)", ln=True, align='C')
    pdf.ln(6)

    # --- Column widths (total usable landscape width ~267mm) ---
    # 38 + 55 + 25 + 28 + 28 + 33 + 33 + 33 = 273 (fits fine in landscape)
    col_date     = 38
    col_item     = 55
    col_action   = 25
    col_qty      = 28
    col_stock    = 28
    col_cost     = 33
    col_sell     = 33
    col_profit   = 33

    # --- Table Headers ---
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(220, 220, 220)

    pdf.cell(col_date,   10, "Date & Time",    border=1, align='C', fill=True)
    pdf.cell(col_item,   10, "Item",           border=1, align='C', fill=True)
    pdf.cell(col_action, 10, "Action",         border=1, align='C', fill=True)
    pdf.cell(col_qty,    10, "Quantity",       border=1, align='C', fill=True)
    pdf.cell(col_stock,  10, "Stock Left",     border=1, align='C', fill=True)
    pdf.cell(col_cost,   10, "Cost Price",     border=1, align='C', fill=True)
    pdf.cell(col_sell,   10, "Selling Price",  border=1, align='C', fill=True)
    pdf.cell(col_profit, 10, "Profit",         border=1, align='C', fill=True)
    pdf.ln()

    # --- Table Data ---
    pdf.set_font("Arial", '', 9)

    total_profit = 0.0

    for log, cost_price, selling_price in results:
        # 1. Date
        date_str = log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "N/A"

        # 2. Item Name
        item_name = str(getattr(log, 'product_name_english', 'Unknown'))

        # 3. Action
        action = str(getattr(log, 'action_type', 'N/A'))

        # 4. Quantity
        qty_val = getattr(log, 'quantity_changed', 0)
        unit_val = getattr(log, 'unit', '')
        if isinstance(qty_val, float) and qty_val.is_integer():
            qty_val = int(qty_val)
        qty_str = f"{qty_val} {unit_val}".strip()

        # 5. Stock after transaction
        stock_val = getattr(log, 'stock_after_transaction', 0)
        if isinstance(stock_val, float) and stock_val.is_integer():
            stock_val = int(stock_val)
        stock_str = f"{stock_val} {unit_val}".strip()

        # 6. Prices (handle None gracefully)
        cost  = float(cost_price)     if cost_price     is not None else 0.0
        sell  = float(selling_price)  if selling_price  is not None else 0.0
        qty_num = float(getattr(log, 'quantity_changed', 0))

        # 7. Profit for this row
        row_profit = (sell - cost) * qty_num
        total_profit += row_profit

        # Colour rows red if loss, green if profit
        if row_profit < 0:
            pdf.set_text_color(180, 0, 0)
        elif row_profit > 0:
            pdf.set_text_color(0, 130, 0)
        else:
            pdf.set_text_color(0, 0, 0)

        profit_str = f"{'- ' if row_profit < 0 else ''}Rs {abs(row_profit):,.2f}"

        pdf.cell(col_date,   10, date_str,              border=1)
        pdf.cell(col_item,   10, item_name,             border=1)
        pdf.cell(col_action, 10, action,                border=1, align='C')
        pdf.cell(col_qty,    10, qty_str,               border=1, align='C')
        pdf.cell(col_stock,  10, stock_str,             border=1, align='C')
        pdf.cell(col_cost,   10, f"Rs {cost:,.2f}",    border=1, align='R')
        pdf.cell(col_sell,   10, f"Rs {sell:,.2f}",    border=1, align='R')
        pdf.cell(col_profit, 10, profit_str,            border=1, align='R')
        pdf.ln()

    # Reset text colour
    pdf.set_text_color(0, 0, 0)

    # --- Total Profit Summary ---
    pdf.ln(6)
    pdf.set_font("Arial", 'B', 11)

    label = f"Total Profit (Last {days} Days):"
    total_str = f"{'- ' if total_profit < 0 else ''}Rs {abs(total_profit):,.2f}"

    if total_profit < 0:
        pdf.set_text_color(180, 0, 0)
    elif total_profit > 0:
        pdf.set_text_color(0, 130, 0)

    pdf.cell(0, 10, f"{label}  {total_str}", ln=True, align='R')
    pdf.set_text_color(0, 0, 0)

    # --- Footer timestamp ---
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 8, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='L')

    output = pdf.output(dest='S')
    if isinstance(output, str):
        return output.encode('latin-1')
    return bytes(output)
