import os
from werkzeug.utils import secure_filename
from config import Config

def sanitize_file(filename: str) -> tuple[bool, str]:
    """Validates extension and sanitizes filename against path traversal."""
    clean_name = secure_filename(filename)
    if not clean_name:
        return False, ""
        
    ext = os.path.splitext(clean_name)[1].lower()
    if ext not in Config.ALLOWED_EXTENSIONS:
        return False, ""
        
    return True, clean_name