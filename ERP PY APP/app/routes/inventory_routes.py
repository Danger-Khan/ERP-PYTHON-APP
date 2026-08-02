from flask import Blueprint, request, jsonify, session
from app.utils.excel_db import ExcelDB
from app.services.query_engine import process_query
from app.security.auth import requires_auth, requires_role
from app.models.schemas import InventoryItemModel
from app.utils.logger import log_event

inventory_bp = Blueprint('inventory', __name__)
db = ExcelDB('inventory')

@inventory_bp.route('/', methods=['GET'])
@requires_auth
def get_inventory():
    search = request.args.get('search')
    category = request.args.get('category')
    low_stock_only = request.args.get('low_stock', 'false').lower() == 'true'

    items = db.get_all()
    
    # Flag items that are below minimum threshold
    processed_items = []
    for item in items:
        item_qty = float(item.get('stock_quantity', 0))
        min_alert = float(item.get('min_stock_alert', 10))
        item['low_stock_warning'] = item_qty <= min_alert
        processed_items.append(item)

    filters = {}
    if category:
        filters['category'] = category
    if low_stock_only:
        processed_items = [i for i in processed_items if i['low_stock_warning']]

    result = process_query(processed_items, search=search, filters=filters, sort_by='item_name')
    return jsonify(result), 200

@inventory_bp.route('/', methods=['POST'])
@requires_auth
@requires_role('Administrator', 'Manager')
def update_stock():
    data = request.json or {}
    code = data.get('item_code') or f"FAB-{len(db.get_all()) + 1:02d}"

    item = InventoryItemModel(
        item_code=code,
        item_name=data.get('item_name', ''),
        category=data.get('category', 'Fabric'),
        stock_quantity=float(data.get('stock_quantity', 0.0)),
        unit=data.get('unit', 'Meters'),
        min_stock_alert=float(data.get('min_stock_alert', 10.0)),
        unit_cost=float(data.get('unit_cost', 0.0)),
        selling_price=float(data.get('selling_price', 0.0)),
        supplier=data.get('supplier', '')
    )

    record = item.to_dict()
    db.save_record(record, id_field='item_code')
    log_event("INVENTORY_SAVE", f"Updated inventory item {item.item_name} ({item.stock_quantity} {item.unit})", user=session.get('username'))

    return jsonify({"message": "Inventory updated successfully", "item": record}), 201