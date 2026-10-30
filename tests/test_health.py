"""
GRIDWISE AI - Health Check Endpoint Tests
Tests verification of /health and /api/health endpoints.
"""

import pytest
from app import create_app
from database.database import init_db


@pytest.fixture
def client():
    """Create test client configured for in-memory testing."""
    app = create_app("testing")
    with app.app_context():
        init_db(":memory:")
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint_status_code(client):
    """Verify /health returns HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_api_health_endpoint_status_code(client):
    """Verify /api/health alias returns HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_payload_structure(client):
    """Verify health JSON response contains mandatory architectural fields."""
    response = client.get("/health")
    data = response.get_json()

    assert data is not None
    assert data["status"] in ["HEALTHY", "DEGRADED"]
    assert "service" in data
    assert data["service"] == "GRIDWISE AI"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "timestamp_utc" in data
    assert "environment" in data
    assert "components" in data

    components = data["components"]
    assert "database" in components
    assert "optimization_engine" in components
    assert "web_server" in components

    assert components["optimization_engine"]["status"] == "READY"
    assert components["web_server"]["status"] == "RUNNING"

