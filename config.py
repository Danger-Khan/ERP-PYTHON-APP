import os

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    BACKUP_DIR = os.path.join(DATA_DIR, 'backups')
    UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-atelier-key-change-in-production')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit
    
    ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.txt', '.json'}
    
    # Ensure directories exist
    for d in [DATA_DIR, BACKUP_DIR, UPLOAD_DIR]:
        os.makedirs(d, exist_ok=True)
