from datetime import datetime
from flask import Blueprint, request, jsonify, session
from app.utils.excel_db import ExcelDB
from app.security.auth import hash_password, check_password, requires_auth, requires_role
from app.utils.logger import log_event

auth_bp = Blueprint('auth', __name__)
db = ExcelDB('users')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    users = db.get_all()
    user = next((u for u in users if str(u.get('username')).lower() == username.lower()), None)

    if not user or not check_password(password, str(user.get('password_hash', ''))):
        log_event("AUTH_FAILED", f"Failed login attempt for user: {username}")
        return jsonify({"error": "Invalid username or password"}), 401

    session['user_id'] = str(user.get('id'))
    session['username'] = str(user.get('username'))
    session['role'] = str(user.get('role', 'Viewer'))

    log_event("AUTH_SUCCESS", f"User logged in: {username}", user=username)

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.get('id'),
            "username": user.get('username'),
            "role": user.get('role')
        }
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    user = session.get('username', 'Unknown')
    session.clear()
    log_event("AUTH_LOGOUT", f"User logged out", user=user)
    return jsonify({"message": "Logged out successfully"}), 200

@auth_bp.route('/users', methods=['POST'])
@requires_auth
@requires_role('Administrator')
def create_user():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'Tailor')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    existing_users = db.get_all()
    if any(u.get('username') == username for u in existing_users):
        return jsonify({"error": "Username already exists"}), 409

    new_user = {
        "id": f"USR-{len(existing_users) + 101}",
        "username": username,
        "password_hash": hash_password(password),
        "role": role,
        "created_at": datetime.now().strftime("%Y-%m-%d")
    }

    db.save_record(new_user, id_field='id')
    log_event("USER_CREATED", f"Created user {username} with role {role}", user=session.get('username'))
    return jsonify({"message": "User created successfully", "user_id": new_user['id']}), 201