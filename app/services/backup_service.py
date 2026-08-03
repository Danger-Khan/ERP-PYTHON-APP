import os
import shutil
import zipfile
from datetime import datetime
from config import Config
from app.utils.logger import log_event

class BackupEngine:

    @staticmethod
    def create_full_backup() -> str:
        """Compresses the entire ./data directory into a timestamped zip backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_atelier_{timestamp}.zip"
        backup_path = os.path.join(Config.BACKUP_DIR, backup_filename)

        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(Config.DATA_DIR):
                for file in files:
                    if not file.endswith('.zip') and not file.endswith('.lock'):
                        full_file_path = os.path.join(root, file)
                        arcname = os.path.relpath(full_file_path, Config.DATA_DIR)
                        zipf.write(full_file_path, arcname)

        log_event("BACKUP_CREATED", f"Created complete system backup archive: {backup_filename}")
        return backup_path

    @staticmethod
    def list_backups() -> list[dict]:
        """Lists all existing backup archives."""
        backups = []
        for file in os.listdir(Config.BACKUP_DIR):
            if file.endswith('.zip'):
                path = os.path.join(Config.BACKUP_DIR, file)
                size_kb = round(os.path.getsize(path) / 1024, 1)
                mod_time = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M')
                backups.append({"filename": file, "size": f"{size_kb} KB", "created_at": mod_time})
        return backups