import os
import logging
from datetime import datetime
from typing import List
from config import Config

LOG_FILE = os.path.join(Config.DATA_DIR, "system_audit.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log_event(event_type: str, message: str, user: str = "System"):
    """Logs security, transactional, and administrative actions."""
    entry = f"[{user}] [{event_type.upper()}] - {message}"
    logging.info(entry)

def get_recent_logs(limit: int = 50) -> List[str]:
    """Retrieves the last N log entries for administrative review."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        return [line.strip() for line in lines[-limit:]]