import html
from datetime import datetime
from app.models.schemas import OrderModel

class InvoiceEngine:
    
    SHOP_NAME = "ATELIER TAILORING & DESIGN STUDIO"
    SHOP_ADDRESS = "Main Boulevard, Suite #4, Commercial Area"
    SHOP_PHONE = "+92 300 1234567"

    @classmethod
    def generate_thermal_text_receipt(cls, order: dict) -> str:
        """Formats an 80mm printable plain-text thermal receipt."""
        inv_no = str(order.get('invoice_number', 'N/A'))
        cust_name = str(order.get('customer_name', 'Walk-in Customer'))
        garment = str(order.get('garment_type', 'Custom Suit'))
        price = float(order.get('price', 0.0))
        advance = float(order.get('advance_payment', 0.0))
        discount = float(order.get('discount', 0.0))
        balance = max(0.0, (price - discount) - advance)
        date_str = str(order.get('order_date', datetime.now().strftime("%Y-%m-%d")))
        due_date = str(order.get('delivery_date', 'N/A'))

        divider = "=" * 32
        sub_divider = "-" * 32

        receipt = f"""
{cls.SHOP_NAME.center(32)}
{cls.SHOP_ADDRESS.center(32)}
{cls.SHOP_PHONE.center(32)}
{divider}
Invoice #: {inv_no:<21}
Date     : {date_str:<21}
Due Date : {due_date:<21}
Customer : {cust_name[:21]:<21}
{sub_divider}
Item / Description           Qty
{sub_divider}
{garment[:26]:<26}  1
{sub_divider}
Total Price : PKR {price:>11.2f}
Discount    : PKR {discount:>11.2f}
Advance Paid: PKR {advance:>11.2f}
{divider}
BALANCE DUE : PKR {balance:>11.2f}
{divider}
      Thank you for your visit!
   Please bring receipt for pickup.
"""
        return receipt

    @classmethod
    def generate_printable_html_invoice(cls, order: dict) -> str:
        """Generates clean HTML invoice markup ready for print preview."""
        inv_no = html.escape(str(order.get('invoice_number', 'N/A')))
        cust_name = html.escape(str(order.get('customer_name', 'Customer')))
        garment = html.escape(str(order.get('garment_type', 'Garment')))
        price = float(order.get('price', 0.0))
        advance = float(order.get('advance_payment', 0.0))
        discount = float(order.get('discount', 0.0))
        balance = max(0.0, (price - discount) - advance)

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Invoice {inv_no}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; padding: 20px; color: #333; }}
        .invoice-card {{ border: 1px solid #ccc; max-width: 600px; margin: auto; padding: 25px; border-radius: 8px; }}
        .header {{ text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
        .details {{ display: flex; justify-content: space-between; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #ddd; text-align: left; }}
        .total-row {{ font-weight: bold; background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <div class="invoice-card">
        <div class="header">
            <h2>{cls.SHOP_NAME}</h2>
            <p>{cls.SHOP_ADDRESS} | {cls.SHOP_PHONE}</p>
        </div>
        <div class="details">
            <div>
                <strong>Customer:</strong> {cust_name}<br>
                <strong>Garment:</strong> {garment}
            </div>
            <div>
                <strong>Invoice:</strong> {inv_no}<br>
                <strong>Date:</strong> {order.get('order_date', '')}
            </div>
        </div>
        <table>
            <thead>
                <tr><th>Description</th><th>Amount (PKR)</th></tr>
            </thead>
            <tbody>
                <tr><td>{garment} Stitching & Tailoring</td><td>{price:.2f}</td></tr>
                <tr><td>Discount Applied</td><td>-{discount:.2f}</td></tr>
                <tr><td>Advance Deposit Paid</td><td>-{advance:.2f}</td></tr>
                <tr class="total-row"><td>Remaining Balance Due</td><td>PKR {balance:.2f}</td></tr>
            </tbody>
        </table>
    </div>
</body>
</html>"""