import os
from flask import Blueprint, jsonify, send_file
from config import Config
from app.services.backup_service import BackupEngine
from app.security.auth import requires_auth, requires_role
from app.utils.logger import log_event

backup_bp = Blueprint('backups', __name__)

@backup_bp.route('/', methods=['GET'])
@requires_auth
@requires_role('Administrator')
def list_backups():
    backups = BackupEngine.list_backups()
    return jsonify({"backups": backups}), 200

@backup_bp.route('/create', methods=['POST'])
@requires_auth
@requires_role('Administrator')
def create_backup():
    try:
        backup_path = BackupEngine.create_full_backup()
        return jsonify({"message": "Full system backup created successfully", "path": backup_path}), 201
    except Exception as e:
        return jsonify({"error": f"Backup creation failed: {str(e)}"}), 500

@backup_bp.route('/download/<filename>', methods=['GET'])
@requires_auth
@requires_role('Administrator')
def download_backup(filename):
    backups = BackupEngine.list_backups()
    matched = next((b for b in backups if b['filename'] == filename), None)
    
    if not matched:
        return jsonify({"error": "Backup file not found"}), 404

    file_path = os.path.join(Config.BACKUP_DIR, filename)
    return send_file(file_path, as_attachment=True)