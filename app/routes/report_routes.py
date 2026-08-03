from flask import Blueprint, request, jsonify, send_file
from app.utils.excel_db import ExcelDB
from app.services.report_service import ReportExporter
from app.security.auth import requires_auth, requires_role

report_bp = Blueprint('reports', __name__)

@report_bp.route('/export/<dataset>', methods=['GET'])
@requires_auth
@requires_role('Administrator', 'Manager')
def export_dataset(dataset):
    export_format = request.args.get('format', 'csv').lower()
    
    # Supported datasets
    valid_tables = ['customers', 'orders', 'employees', 'inventory']
    if dataset not in valid_tables:
        return jsonify({"error": f"Invalid dataset. Must be one of {valid_tables}"}), 400

    db = ExcelDB(dataset)
    data = db.get_all()

    if not data:
        return jsonify({"error": f"No records found in {dataset} to export"}), 404

    if export_format == 'excel':
        stream, filename = ReportExporter.export_to_excel(data, sheet_name=dataset.capitalize(), filename=f"{dataset}_report")
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        stream, filename = ReportExporter.export_to_csv(data, filename=f"{dataset}_report")
        mimetype = "text/csv"

    return send_file(
        stream,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )