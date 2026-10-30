"""
GRIDWISE AI - Blueprints Initialization and Registration.
"""

from .main import main_bp
from .dashboard import dashboard_bp
from .optimization import optimization_bp
from .analytics import analytics_bp
from .reports import reports_bp
from .forecasting import forecasting_bp
from .adaptive import adaptive_bp
from .decision_intelligence import decision_bp
from .auth import auth_bp
from .system import system_bp


def register_blueprints(app):
    """Register all Flask blueprints on the application instance."""
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(optimization_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(forecasting_bp)
    app.register_blueprint(adaptive_bp)
    app.register_blueprint(decision_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(system_bp)


__all__ = ["register_blueprints"]
