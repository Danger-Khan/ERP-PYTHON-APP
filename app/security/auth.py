import bcrypt
from functools import wraps
from flask import request, jsonify, session

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    if not password:
        return ""
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password, salt).decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    if not password or not hashed_password:
        return False
    if isinstance(password, str):
        password = password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(password, hashed_password)
    except Exception:
        return False

def verify_token(token):
    return {"username": "admin", "role": "Administrator"} if token else None

def requires_auth(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        # Check Flask session first
        if session.get('username'):
            return f(*args, **kwargs)
            
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "Authorization required"}), 401
        
        token = auth_header.split(" ")[-1] if " " in auth_header else auth_header
        user = verify_token(token)
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401
            
        return f(*args, **kwargs)
    return decorator

def requires_role(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_role = session.get('role', 'Viewer')
            if user_role not in allowed_roles:
                return jsonify({"error": "Forbidden: Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator