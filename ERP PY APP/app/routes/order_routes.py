from flask import Blueprint, request, jsonify, session
from app.utils.excel_db import ExcelDB
from app.services.query_engine import process_query
from app.security.auth import requires_auth, requires_role
from app.models.schemas import OrderModel
from app.utils.logger import log_event

order_bp = Blueprint('orders', __name__)
db = ExcelDB('orders')

@order_bp.route('/', methods=['GET'])
@requires_auth
def list_orders():
    search = request.args.get('search')
    status = request.args.get('status')
    tailor = request.args.get('tailor')
    sort_by = request.args.get('sort_by', 'order_date')
    sort_desc = request.args.get('sort_desc', 'true').lower() == 'true'
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 25))

    filters = {}
    if status:
        filters['status'] = status
    if tailor:
        filters['assigned_tailor'] = tailor

    orders = db.get_all()
    result = process_query(orders, search=search, filters=filters, sort_by=sort_by, sort_desc=sort_desc, page=page, limit=limit)
    return jsonify(result), 200

@order_bp.route('/', methods=['POST'])
@requires_auth
@requires_role('Administrator', 'Manager', 'Tailor')
def save_order():
    data = request.json or {}
    order_id = data.get('id') or f"ORD-{len(db.get_all()) + 101}"
    invoice_num = data.get('invoice_number') or f"INV-{len(db.get_all()) + 1001}"

    order = OrderModel(
        id=order_id,
        invoice_number=invoice_num,
        customer_id=data.get('customer_id', ''),
        customer_name=data.get('customer_name', 'Walk-in'),
        garment_type=data.get('garment_type', 'Shalwar Kameez'),
        status=data.get('status', 'Pending'),
        assigned_tailor=data.get('assigned_tailor', 'Unassigned'),
        price=float(data.get('price', 0.0)),
        advance_payment=float(data.get('advance_payment', 0.0)),
        discount=float(data.get('discount', 0.0)),
        priority=data.get('priority', 'Normal'),
        delivery_date=data.get('delivery_date', ''),
        measurements_snapshot=str(data.get('measurements_snapshot', '')),
        notes=data.get('notes', '')
    )

    record = order.to_dict()
    db.save_record(record, id_field='id')
    log_event("ORDER_SAVE", f"Saved order {order.id} for {order.customer_name}", user=session.get('username', 'System'))

    return jsonify({"message": "Order saved successfully", "order": record}), 201

@order_bp.route('/<order_id>/status', methods=['PATCH'])
@requires_auth
def update_status(order_id):
    data = request.json or {}
    new_status = data.get('status')
    if not new_status:
        return jsonify({"error": "New status is required"}), 400

    orders = db.get_all()
    order = next((o for o in orders if o.get('id') == order_id), None)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    order['status'] = new_status
    db.save_record(order, id_field='id')
    log_event("ORDER_STATUS", f"Order {order_id} status updated to {new_status}", user=session.get('username', 'System'))

    return jsonify({"message": "Order status updated", "order_id": order_id, "status": new_status}), 200