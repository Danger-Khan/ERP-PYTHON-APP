import os
import time
from flask import Blueprint, request, jsonify, send_from_directory
from app.security.validation import sanitize_file
from config import Config

system_bp = Blueprint('system', __name__)

@system_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file submitted'}), 400
        
    file = request.files['file']
    is_safe, clean_name = sanitize_file(file.filename)
    
    if not is_safe:
        return jsonify({'error': 'Invalid file type or filename'}), 403

    filepath = os.path.join(Config.UPLOAD_DIR, clean_name)
    file.save(filepath)
    # Log system event here
    return jsonify({'status': 'success', 'filename': clean_name})

@system_bp.route('/diagnostics', methods=['GET'])
def run_diagnostics():
    """Checks the status of the local environment."""
    data_size = sum(os.path.getsize(os.path.join(Config.DATA_DIR, f)) for f in os.listdir(Config.DATA_DIR) if os.path.isfile(os.path.join(Config.DATA_DIR, f)))
    
    return jsonify({
        "status": "Online",
        "database": "Excel (OpenPyXL Abstracted)",
        "db_folder_size_kb": round(data_size / 1024, 2),
        "backups_count": len(os.listdir(Config.BACKUP_DIR)),
        "time": time.strftime('%Y-%m-%d %H:%M:%S')
    })