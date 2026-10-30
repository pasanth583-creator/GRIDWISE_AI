"""
GRIDWISE AI - System Administration, Telemetry, and Background Jobs Routes
Provides operational monitoring, health diagnostics, backup management, and async job orchestration.
"""

import os
from flask import Blueprint, render_template, request, jsonify, session, abort
from services.system_health_service import SystemHealthService
from services.application_monitoring import monitoring
from services.backup_service import BackupService
from services.job_manager import job_manager
from services.security_service import login_required, roles_required

system_bp = Blueprint("system", __name__)

# ---------------------------------------------------------
# Health and Telemetry Endpoints
# ---------------------------------------------------------

@system_bp.route("/health", methods=["GET"])
def health_check():
    """Standard health check endpoint for reverse proxies and orchestrators."""
    diagnostics = SystemHealthService.get_full_diagnostics()
    status_code = 200 if diagnostics["status"] in ["healthy", "degraded"] else 503
    return jsonify({
        "status": diagnostics["status"],
        "application": "GRIDWISE AI",
        "version": "1.0.0",
        "timestamp": diagnostics["timestamp"],
        "database": diagnostics["components"]["database"]["status"],
        "solver": diagnostics["components"]["solver"]["status"]
    }), status_code


@system_bp.route("/api/system/health", methods=["GET"])
def system_health_api():
    """Full deep diagnostic report across database, solver, forecasting, and storage."""
    diagnostics = SystemHealthService.get_full_diagnostics()
    return jsonify(diagnostics)


@system_bp.route("/api/system/metrics", methods=["GET"])
def system_metrics_api():
    """Application telemetry: request rates, status breakdown, latencies, and uptime."""
    metrics = monitoring.get_metrics_summary()
    return jsonify({
        "status": "success",
        "metrics": metrics
    })


# ---------------------------------------------------------
# Database Backup & Recovery Endpoints
# ---------------------------------------------------------

@system_bp.route("/api/system/backup", methods=["POST"])
@roles_required("admin", "operator")
def trigger_backup():
    """Triggers an online point-in-time hot backup of the SQLite database."""
    tag = request.json.get("tag", "manual") if request.is_json else "manual"
    res = BackupService.backup_database(tag=tag)
    status_code = 200 if res.get("status") == "success" else 500
    return jsonify(res), status_code


@system_bp.route("/api/system/backups", methods=["GET"])
def list_backups_api():
    """Lists existing database backups and their integrity status."""
    backups = BackupService.list_backups()
    return jsonify({
        "status": "success",
        "count": len(backups),
        "backups": backups
    })


@system_bp.route("/api/system/restore", methods=["POST"])
@roles_required("admin")
def restore_backup():
    """Restores database from an existing verified backup file."""
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    if not filename:
        return jsonify({"status": "error", "message": "Missing 'filename' parameter"}), 400
        
    res = BackupService.restore_database(filename)
    status_code = 200 if res.get("status") == "success" else 400
    return jsonify(res), status_code


# ---------------------------------------------------------
# Background Job Orchestration Endpoints
# ---------------------------------------------------------

@system_bp.route("/api/jobs/optimization", methods=["POST"])
def enqueue_optimization():
    """Enqueues an asynchronous stochastic optimization background job."""
    data = request.get_json(silent=True) or {}
    scenarios_count = int(data.get("scenarios_count", 100))
    risk_lambda = float(data.get("risk_lambda", 0.0))
    user_id = session.get("user", "api_client")
    
    job_uuid = job_manager.enqueue_optimization_job(
        scenarios_count=scenarios_count,
        risk_lambda=risk_lambda,
        user_id=user_id
    )
    
    monitoring.record_optimization_run()
    
    return jsonify({
        "status": "queued",
        "job_uuid": job_uuid,
        "message": "Optimization job queued successfully for background execution.",
        "params": {
            "scenarios_count": scenarios_count,
            "risk_lambda": risk_lambda
        }
    }), 202


@system_bp.route("/api/jobs", methods=["GET"])
def list_jobs():
    """Returns list of recent background jobs."""
    limit = int(request.args.get("limit", 20))
    jobs = job_manager.list_recent_jobs(limit=limit)
    return jsonify({
        "status": "success",
        "count": len(jobs),
        "jobs": jobs
    })


@system_bp.route("/api/jobs/<job_uuid>", methods=["GET"])
def get_job_status(job_uuid):
    """Retrieves current execution state and results of a background job."""
    job = job_manager.get_job_status(job_uuid)
    if not job:
        return jsonify({"status": "error", "message": f"Job {job_uuid} not found"}), 404
    return jsonify({
        "status": "success",
        "job": job
    })


@system_bp.route("/api/jobs/<job_uuid>/cancel", methods=["POST"])
@roles_required("admin", "operator")
def cancel_job(job_uuid):
    """Cancels a pending or queued background job."""
    res = job_manager.cancel_job(job_uuid)
    status_code = 200 if res.get("status") == "success" else 400
    return jsonify(res), status_code


# ---------------------------------------------------------
# System Administration Dashboard UI
# ---------------------------------------------------------

@system_bp.route("/system")
def system_status_view():
    """Renders the comprehensive System Administration, Jobs & Health Dashboard."""
    diagnostics = SystemHealthService.get_full_diagnostics()
    metrics = monitoring.get_metrics_summary()
    backups = BackupService.list_backups()[:5]
    recent_jobs = job_manager.list_recent_jobs(limit=10)
    
    return render_template(
        "system_status.html",
        active_page="system",
        page_title="System Administration & Telemetry",
        diagnostics=diagnostics,
        metrics=metrics,
        backups=backups,
        recent_jobs=recent_jobs
    )

