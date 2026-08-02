from flask import Flask
from flask_cors import CORS
from config import Config
from app.utils.excel_db import initialize_database

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, supports_credentials=True)

    # Initialize Excel Database
    initialize_database()

    # Register All Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.customer_routes import customer_bp
    from app.routes.order_routes import order_bp
    from app.routes.employee_routes import employee_bp
    from app.routes.inventory_routes import inventory_bp
    from app.routes.finance_routes import finance_bp
    from app.routes.analytics_routes import analytics_bp
    from app.routes.report_routes import report_bp
    from app.routes.backup_routes import backup_bp
    from app.routes.system_routes import system_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(customer_bp, url_prefix='/api/customers')
    app.register_blueprint(order_bp, url_prefix='/api/orders')
    app.register_blueprint(employee_bp, url_prefix='/api/employees')
    app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
    app.register_blueprint(finance_bp, url_prefix='/api/finance')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(report_bp, url_prefix='/api/reports')
    app.register_blueprint(backup_bp, url_prefix='/api/backups')
    app.register_blueprint(system_bp, url_prefix='/api/system')

    return app