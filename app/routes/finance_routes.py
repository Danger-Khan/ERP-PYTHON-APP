from datetime import datetime
from flask import Blueprint, request, jsonify
from app.utils.excel_db import ExcelDB
from app.security.auth import requires_auth, requires_role
from app.utils.logger import log_event

finance_bp = Blueprint('finance', __name__)
orders_db = ExcelDB('orders')
expenses_db = ExcelDB('expenses')

@finance_bp.route('/summary', methods=['GET'])
@requires_auth
@requires_role('Administrator', 'Manager')
def financial_summary():
    orders = orders_db.get_all()
    expenses = expenses_db.get_all()

    # Calculate Revenue
    total_revenue = sum(float(o.get('price', 0)) - float(o.get('discount', 0)) for o in orders if o.get('status') != 'Cancelled')
    collected_cash = sum(float(o.get('advance_payment', 0)) for o in orders)
    pending_cash = sum(float(o.get('remaining_balance', 0)) for o in orders if o.get('status') != 'Delivered')

    # Calculate Expenses
    total_expenses = sum(float(e.get('amount', 0)) for e in expenses)
    net_profit = total_revenue - total_expenses

    return jsonify({
        "summary": {
            "total_revenue": total_revenue,
            "cash_collected": collected_cash,
            "pending_payments": pending_cash,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "margin_percentage": round((net_profit / total_revenue * 100), 2) if total_revenue > 0 else 0
        }
    }), 200

@finance_bp.route('/expense', methods=['POST'])
@requires_auth
@requires_role('Administrator', 'Manager')
def record_expense():
    data = request.json or {}
    expense_id = f"EXP-{len(expenses_db.get_all()) + 1:03d}"

    record = {
        "id": expense_id,
        "title": data.get('title', 'General Expense'),
        "category": data.get('category', 'Utilities'), # Salaries, Rent, Utilities, Threads/Material
        "amount": float(data.get('amount', 0.0)),
        "date": data.get('date', datetime.now().strftime("%Y-%m-%d")),
        "notes": data.get('notes', '')
    }

    expenses_db.save_record(record, id_field='id')
    log_event("EXPENSE_ADDED", f"Recorded expense PKR {record['amount']} for {record['title']}")
    return jsonify({"message": "Expense recorded successfully", "expense": record}), 201