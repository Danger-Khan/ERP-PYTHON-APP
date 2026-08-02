from flask import Blueprint, request, jsonify
from app.utils.excel_db import ExcelDB
from app.services.query_engine import process_query
from app.security.auth import requires_auth, requires_role

customer_bp = Blueprint('customers', __name__)
db = ExcelDB('customers')

@customer_bp.route('/', methods=['GET'])
@requires_auth
def get_customers():
    try:
        # Extract query parameters
        search = request.args.get('search')
        sort_by = request.args.get('sort_by')
        sort_desc = request.args.get('sort_desc', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 25))
        
        # Example specific filter (e.g., gender)
        gender = request.args.get('gender')
        filters = {'gender': gender} if gender else None

        raw_data = db.get_all()
        response = process_query(raw_data, search, filters, sort_by, sort_desc, page, limit)
        
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@customer_bp.route('/', methods=['POST'])
@requires_auth
@requires_role('Admin', 'Manager', 'Tailor')
def save_customer():
    data = request.json
    
    # Input Validation Example
    if not data.get('id') or not data.get('name'):
        return jsonify({"error": "Missing required fields: id, name"}), 400

    try:
        db.save_record(data, id_field='id')
        return jsonify({"message": "Customer saved successfully", "customer": data}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to save: {str(e)}"}), 500