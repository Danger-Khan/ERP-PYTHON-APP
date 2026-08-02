from flask import Blueprint, request, jsonify, session
from app.utils.excel_db import ExcelDB
from app.services.query_engine import process_query
from app.security.auth import requires_auth, requires_role
from app.models.schemas import EmployeeModel
from app.utils.logger import log_event

employee_bp = Blueprint('employees', __name__)
db = ExcelDB('employees')

@employee_bp.route('/', methods=['GET'])
@requires_auth
def list_employees():
    search = request.args.get('search')
    duty_status = request.args.get('status')
    role = request.args.get('role')

    filters = {}
    if duty_status:
        filters['status'] = duty_status
    if role:
        filters['role'] = role

    staff = db.get_all()
    res = process_query(staff, search=search, filters=filters, sort_by='name')
    return jsonify(res), 200

@employee_bp.route('/', methods=['POST'])
@requires_auth
@requires_role('Administrator', 'Manager')
def save_employee():
    data = request.json or {}
    emp_id = data.get('id') or f"E-{len(db.get_all()) + 1:02d}"

    employee = EmployeeModel(
        id=emp_id,
        name=data.get('name', ''),
        phone=data.get('phone', ''),
        role=data.get('role', 'Stitching Specialist'),
        status=data.get('status', 'On Duty'),
        salary=float(data.get('salary', 0.0)),
        cnic=data.get('cnic', ''),
        current_task=data.get('current_task', 'None'),
        specialization=data.get('specialization', 'General')
    )

    record = employee.to_dict()
    db.save_record(record, id_field='id')
    log_event("EMP_UPDATE", f"Updated employee profile for {employee.name}", user=session.get('username'))
    return jsonify({"message": "Employee record saved", "employee": record}), 201

@employee_bp.route('/assign_task', methods=['POST'])
@requires_auth
def assign_task():
    data = request.json or {}
    emp_id = data.get('employee_id')
    task_desc = data.get('task')

    if not emp_id or not task_desc:
        return jsonify({"error": "Employee ID and Task description are required"}), 400

    staff = db.get_all()
    emp = next((e for e in staff if e.get('id') == emp_id), None)
    if not emp:
        return jsonify({"error": "Staff member not found"}), 404

    emp['current_task'] = task_desc
    db.save_record(emp, id_field='id')
    log_event("TASK_ASSIGNED", f"Assigned task to {emp.get('name')}: {task_desc}", user=session.get('username'))

    return jsonify({"message": "Task assigned successfully", "employee_id": emp_id}), 200