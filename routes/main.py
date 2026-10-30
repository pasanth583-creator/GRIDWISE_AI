"""
GRIDWISE AI - Main Blueprint
Core routes, health checks, and system diagnostics.
"""

import time
import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, render_template, redirect, url_for, current_app
from database.database import check_db_health
from services import MicrogridService

main_bp = Blueprint("main", __name__)

START_TIME = time.time()


@main_bp.route("/")
def index():
    """Root landing page redirects to the primary dashboard."""
    return redirect(url_for("dashboard.dashboard_view"))


@main_bp.route("/health")
@main_bp.route("/api/health")
def health_check():
    """
    Comprehensive system health-check endpoint.
    Returns JSON status with DB connectivity, uptime, environment, and version.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)
    db_health = check_db_health()

    is_healthy = db_health.get("connected", False)
    status_str = "HEALTHY" if is_healthy else "DEGRADED"
    http_code = 200 if is_healthy else 503

    response_payload = {
        "status": status_str,
        "service": current_app.config.get("PROJECT_NAME", "GRIDWISE AI"),
        "title": current_app.config.get("PROJECT_TITLE", "Microgrid Stochastic Optimization"),
        "version": current_app.config.get("VERSION", "1.0.0"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "environment": os.environ.get("FLASK_ENV", "development"),
        "components": {
            "database": db_health,
            "optimization_engine": {
                "status": "READY",
                "phase": "Phase 1: Foundation",
                "solvers_supported": [
                    "SciPy HiGHS (Interior Point)",
                    "SciPy HiGHS (Dual Simplex)",
                ],
            },
            "web_server": {
                "status": "RUNNING",
                "framework": "Flask 3.x",
            },
        },
    }

    return jsonify(response_payload), http_code


@main_bp.route("/api/status")
def system_status():
    """Provides high-level system metrics and configuration summary."""
    summary = MicrogridService.get_system_summary()
    return jsonify(summary), 200

