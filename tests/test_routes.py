"""
GRIDWISE AI - Routes and Blueprints Test Suite
Validates that all route blueprints render templates and return expected HTTP status.
"""

import pytest
from app import create_app
from database.database import init_db


@pytest.fixture
def client():
    """Create test client with initialized database."""
    app = create_app("testing")
    with app.app_context():
        init_db(":memory:")
    with app.test_client() as test_client:
        yield test_client


def test_root_redirect(client):
    """Root URL should redirect to the executive dashboard."""
    response = client.get("/")
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_dashboard_view(client):
    """Dashboard view should render with status 200."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Overview Dashboard" in response.data
    assert b"GRIDWISE AI" in response.data


def test_monitoring_view(client):
    """Live monitoring view should render with status 200."""
    response = client.get("/monitoring")
    assert response.status_code == 200
    assert b"Energy Monitoring" in response.data


def test_optimization_view(client):
    """Optimization interface should render with status 200."""
    response = client.get("/optimization")
    assert response.status_code == 200
    assert b"Optimization Studio" in response.data or b"Optimization" in response.data


def test_scenarios_view(client):
    """Scenarios interface should render with status 200."""
    response = client.get("/scenarios")
    assert response.status_code == 200
    assert b"Scenario Analysis" in response.data


def test_risk_view(client):
    """Risk & CVaR view should render with status 200."""
    response = client.get("/risk")
    assert response.status_code == 200
    assert b"Risk Management" in response.data or b"Risk" in response.data


def test_battery_view(client):
    """Battery management view should render with status 200."""
    response = client.get("/battery")
    assert response.status_code == 200
    assert b"Battery Management" in response.data or b"Battery" in response.data


def test_solar_view(client):
    """Solar PV view should render with status 200."""
    response = client.get("/solar")
    assert response.status_code == 200
    assert b"Solar Analytics" in response.data or b"Solar" in response.data


def test_costs_view(client):
    """Energy costs and tariff view should render with status 200."""
    response = client.get("/costs")
    assert response.status_code == 200
    assert b"Cost &amp; Savings" in response.data or b"Cost" in response.data


def test_reports_view(client):
    """Reports view should render with status 200."""
    response = client.get("/reports")
    assert response.status_code == 200
    assert b"Reports &amp; Export" in response.data or b"Reports" in response.data


def test_model_view(client):
    """Mathematical formulation view should render with status 200."""
    response = client.get("/model")
    assert response.status_code == 200
    assert b"Model Information" in response.data or b"Stochastic Optimization Model" in response.data


def test_api_status(client):
    """System status API should return microgrid specs and healthy DB."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.get_json()
    assert "microgrid" in data
    assert data["microgrid"]["pv_capacity_kw"] == 800.0
    assert data["microgrid"]["bess_capacity_kwh"] == 1000.0


def test_api_optimization_runs(client):
    """API runs endpoint returns array."""
    response = client.get("/api/optimization/runs")
    assert response.status_code == 200
    data = response.get_json()
    assert "runs" in data
    assert isinstance(data["runs"], list)


def test_api_optimization_parameters(client):
    """API parameters endpoint returns default configurations."""
    response = client.get("/api/optimization/parameters")
    assert response.status_code == 200
    data = response.get_json()
    assert "defaults" in data
    assert "formulations" in data
    assert "solvers" in data


def test_404_error_handler_html(client):
    """Non-existent HTML route returns custom 404 page."""
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    assert b"404" in response.data


def test_404_error_handler_api(client):
    """Non-existent API route returns JSON 404 payload."""
    response = client.get("/api/non-existent-endpoint")
    assert response.status_code == 404
    data = response.get_json()
    assert data is not None
    assert data["error"] == "Not Found"

