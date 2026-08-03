import sys

# 1. Dependency check before attempting imports
try:
    from flask import Flask
    from flask_cors import CORS
except ImportError:
    print("\n" + "=" * 65)
    print("❌ ERROR: Required Python dependencies are not installed!")
    print("Please run this command in your VS Code terminal first:")
    print("    pip install flask flask-cors openpyxl bcrypt filelock")
    print("=" * 65 + "\n")
    sys.exit(1)

# 2. Project modules import with helpful error catch
try:
    from app import create_app
    from app.security.middleware import rate_limit_auth_middleware
    from app.services.scheduler import BackgroundScheduler
except ModuleNotFoundError as e:
    print("\n" + "=" * 65)
    print(f"❌ MODULE ERROR: {str(e)}")
    print("Tip: If it says 'No module named app.services.scheduler':")
    print("     Rename 'app/services/schedular.py' -> 'scheduler.py'")
    print("=" * 65 + "\n")
    sys.exit(1)

# Initialize Flask Application
app = create_app()

# Register Security Middleware
app.before_request(rate_limit_auth_middleware)

# Initialize Threaded Background Worker
scheduler = BackgroundScheduler(interval_seconds=3600)

if __name__ == '__main__':
    scheduler.start()
    print("\n" + "=" * 65)
    print("🚀 Atelier Enterprise Server listening at http://127.0.0.1:5000")
    print("   Press CTRL+C in the terminal to stop the server.")
    print("=" * 65 + "\n")
    
    try:
        app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\nStopping Atelier Server...")
    finally:
        scheduler.stop()
        print("✅ Background scheduler stopped safely.")