"""
GRIDWISE AI - Phase 10 Production & Security Test Suite
Validates authentication, RBAC, hot backups, background jobs, telemetry, and health endpoints.
"""

import pytest
import os
import json
import tempfile
from app import create_app
from database.database import init_db, migrate_phase10_tables
from services.security_service import SecurityService
from services.backup_service import BackupService
from services.job_manager import job_manager

@pytest.fixture
def app_and_client():
    """Configures isolated test client with dedicated SQLite database."""
    fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    init_db(temp_db_path)
    migrate_phase10_tables(temp_db_path)
    SecurityService.seed_default_users(temp_db_path)
    
    app = create_app("testing")
    app.config["DATABASE_PATH"] = temp_db_path
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield app, client, temp_db_path
            
    try:
        os.remove(temp_db_path)
    except Exception:
        pass


def test_health_endpoint(app_and_client):
    """Verifies lightweight /health endpoint returns 200 and healthy status."""
    _, client, _ = app_and_client
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"].upper() in ["HEALTHY", "DEGRADED"]
    assert "GRIDWISE" in (data.get("application") or data.get("service") or "")


def test_system_diagnostics_api(app_and_client):
    """Verifies deep diagnostic telemetry endpoint /api/system/health."""
    _, client, _ = app_and_client
    resp = client.get("/api/system/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "components" in data
    assert data["components"]["database"]["status"] == "healthy"
    assert data["components"]["solver"]["status"] == "healthy"


def test_system_metrics_api(app_and_client):
    """Verifies operational telemetry endpoint /api/system/metrics."""
    _, client, _ = app_and_client
    resp = client.get("/api/system/metrics")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "metrics" in data
    assert "uptime_seconds" in data["metrics"]
    assert "status_breakdown" in data["metrics"]


def test_authentication_workflow(app_and_client):
    """Verifies login, session creation, user info API, and logout."""
    _, client, _ = app_and_client
    
    # 1. Anonymous user info
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.get_json()["authenticated"] is False
    
    # 2. Invalid login attempt
    resp = client.post("/login", data={"username": "admin", "password": "WrongPassword"})
    assert resp.status_code == 401
    
    # 3. Valid admin login
    resp = client.post("/login", data={"username": "admin", "password": "GridWise@Admin2026"}, follow_redirects=True)
    assert resp.status_code == 200
    
    # 4. Authenticated user info
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["authenticated"] is True
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert data["permissions"]["can_restore_backup"] is True
    
    # 5. Logout
    resp = client.get("/logout", follow_redirects=True)
    assert resp.status_code == 200
    resp = client.get("/api/auth/me")
    assert resp.get_json()["authenticated"] is False


def test_csrf_token_endpoint(app_and_client):
    """Verifies CSRF token retrieval endpoint."""
    _, client, _ = app_and_client
    resp = client.get("/api/auth/csrf")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 20


def test_backup_and_recovery_workflow(app_and_client):
    """Verifies online hot backup creation and listing."""
    _, client, db_path = app_and_client
    
    # Authenticate as admin
    client.post("/login", data={"username": "admin", "password": "GridWise@Admin2026"})
    
    # Trigger hot backup
    resp = client.post("/api/system/backup", json={"tag": "test_phase10"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "filename" in data
    
    # List backups
    resp = client.get("/api/system/backups")
    assert resp.status_code == 200
    list_data = resp.get_json()
    assert list_data["count"] >= 1
    assert any(data["filename"] == b["filename"] for b in list_data["backups"])


def test_background_job_orchestration(app_and_client):
    """Verifies async background job queueing, status checking, and retrieval."""
    _, client, _ = app_and_client
    
    # Enqueue optimization job
    resp = client.post("/api/jobs/optimization", json={"scenarios_count": 10, "risk_lambda": 0.0})
    assert resp.status_code == 202
    data = resp.get_json()
    assert data["status"] == "queued"
    job_uuid = data["job_uuid"]
    assert job_uuid is not None
    
    # Retrieve job status
    resp = client.get(f"/api/jobs/{job_uuid}")
    assert resp.status_code == 200
    job_data = resp.get_json()["job"]
    assert job_data["job_uuid"] == job_uuid
    assert job_data["status"] in ["QUEUED", "RUNNING", "COMPLETED"]
    
    # List jobs
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    jobs_list = resp.get_json()["jobs"]
    assert any(j["job_uuid"] == job_uuid for j in jobs_list)


def test_system_status_ui_rendering(app_and_client):
    """Verifies that the System & Operations dashboard renders HTTP 200."""
    _, client, _ = app_and_client
    resp = client.get("/system")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "System Administration" in html
    assert "Background Job Manager" in html
    assert "Hot Database Backups" in html
