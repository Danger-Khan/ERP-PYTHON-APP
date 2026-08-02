import os
import time
import threading
from datetime import datetime
from config import Config
from app.services.backup_service import BackupEngine
from app.utils.logger import log_event

class BackgroundScheduler:
    """Threaded job runner for periodic system maintenance."""

    def __init__(self, interval_seconds: int = 3600):
        self.interval = interval_seconds
        self.running = False
        self.thread = None

    def _run_periodic_jobs(self):
        while self.running:
            try:
                # 1. Automatic Backup Check (Runs around Midnight)
                current_hour = datetime.now().hour
                if current_hour == 0:
                    BackupEngine.create_full_backup()
                    log_event("SCHEDULER", "Automated midnight database backup completed.")

                # 2. Lock & Temp File Cleanup
                self._cleanup_temp_locks()

            except Exception as e:
                log_event("SCHEDULER_ERROR", f"Background worker encountered an error: {str(e)}")

            time.sleep(self.interval)

    def _cleanup_temp_locks(self):
        """Removes orphaned file locks and ancient upload files."""
        for root, _, files in os.walk(Config.DATA_DIR):
            for file in files:
                if file.endswith('.lock'):
                    lock_file = os.path.join(root, file)
                    # Delete lock file if older than 30 minutes
                    if time.time() - os.path.getmtime(lock_file) > 1800:
                        try:
                            os.remove(lock_file)
                            log_event("CLEANUP", f"Removed stale lock file: {file}")
                        except OSError:
                            pass

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_periodic_jobs, daemon=True)
            self.thread.start()
            log_event("SCHEDULER", "Background service scheduler started.")

    def stop(self):
        self.running = False