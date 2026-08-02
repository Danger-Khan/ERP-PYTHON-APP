from flask import Blueprint, jsonify
from app.services.analytics_service import AnalyticsEngine
from app.security.auth import requires_auth

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/dashboard', methods=['GET'])
@requires_auth
def get_dashboard_kpis():
    try:
        summary = AnalyticsEngine.get_dashboard_summary()
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({"error": f"Failed to compute analytics: {str(e)}"}), 500