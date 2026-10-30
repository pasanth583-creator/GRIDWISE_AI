"""
GRIDWISE AI - Application Factory & Server Entrypoint
Risk-Averse Stochastic Day-Ahead Energy Procurement and Battery Dispatch for an Institutional Microgrid
"""

import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from flask import Flask, render_template, request, jsonify, g, session

from config import get_config, BASE_DIR
from database.database import init_app as init_db_app, init_db, check_db_health
from routes import register_blueprints
from services.application_monitoring import monitoring
from services.security_service import SecurityService


def configure_logging(app):
    """Configure structured console and rotating file logging."""
    log_level_name = app.config.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    log_format = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s in %(module)s: %(message)s"
    )

    # Ensure logs directory exists
    log_file_path = Path(app.config.get("LOG_FILE", BASE_DIR / "logs" / "gridwise.log"))
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # File handler with rotation (5MB per file, 3 backups)
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(log_level)

    # Attach to Flask logger and root logger
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Root logger configuration for dependencies
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)


def register_error_handlers(app):
    """Register custom error handlers for HTTP error codes."""

    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith("/api/") or request.is_json:
            return jsonify({
                "error": "Not Found",
                "message": "The requested resource could not be found.",
                "status_code": 404,
                "path": request.path,
            }), 404
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith("/api/") or request.is_json:
            return jsonify({
                "error": "Forbidden",
                "message": "You do not have permission to access this resource.",
                "status_code": 403,
            }), 403
        return render_template("errors/403.html", error=error), 403

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal Server Error: {error}")
        if request.path.startswith("/api/") or request.is_json:
            return jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected error occurred on the server.",
                "status_code": 500,
            }), 500
        return render_template("errors/500.html", error=error), 500

    @app.errorhandler(400)
    def bad_request_error(error):
        if request.path.startswith("/api/") or request.is_json:
            return jsonify({
                "error": "Bad Request",
                "message": str(error),
                "status_code": 400,
            }), 400
        return render_template("errors/404.html", error=error, error_code=400, error_title="Bad Request"), 400


def create_app(config_name=None):
    """Application factory for GRIDWISE AI."""
    app = Flask(__name__)

    # Load configuration
    config_obj = get_config(config_name)
    app.config.from_object(config_obj)

    # Setup Logging
    configure_logging(app)
    app.logger.info(f"Initializing {app.config['PROJECT_NAME']} in {config_obj.__name__} mode")

    # Initialize Database Extensions
    init_db_app(app)

    # Register Blueprints
    register_blueprints(app)

    # Register Error Handlers
    register_error_handlers(app)

    # Telemetry and Security Middleware
    @app.before_request
    def before_request_hook():
        g.start_time = time.time()
        g.current_user = session.get("user", "anonymous")

    @app.after_request
    def after_request_hook(response):
        # Latency calculation
        duration_ms = (time.time() - getattr(g, "start_time", time.time())) * 1000
        monitoring.record_request(
            endpoint=request.endpoint or request.path,
            status_code=response.status_code,
            duration_ms=duration_ms
        )

        # Production Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # Global Template Context
    @app.context_processor
    def inject_global_template_context():
        return {
            "app_name": app.config.get("PROJECT_NAME", "GRIDWISE AI"),
            "project_title": app.config.get(
                "PROJECT_TITLE",
                "Risk-Averse Stochastic Day-Ahead Energy Procurement and Battery Dispatch for an Institutional Microgrid",
            ),
            "version": app.config.get("VERSION", "1.0.0"),
            "current_year": 2026,
            "database_status": check_db_health().get("status", "UNKNOWN"),
            "current_user": session.get("user"),
            "current_role": session.get("role"),
        }

    return app


# Module-level app instance for WSGI / CLI discovery
app = create_app()


if __name__ == "__main__":
    # Ensure database is initialized before serving
    db_file = app.config.get("DATABASE_PATH")
    if db_file and db_file != ":memory:" and not os.path.exists(db_file):
        app.logger.info(f"Database not found at {db_file}, initializing schema...")
        init_db(db_file)

    # Seed default RBAC users if present
    try:
        SecurityService.seed_default_users()
    except Exception as e:
        app.logger.warning(f"Could not seed default users on startup: {e}")

    host = app.config.get("HOST", "127.0.0.1")
    port = app.config.get("PORT", 5000)
    debug = app.config.get("DEBUG", True)

    app.logger.info(f"Starting {app.config['PROJECT_NAME']} on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
