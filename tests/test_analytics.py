"""
Tests for Phase 5 Advanced Analytics and Risk Decision Support Services.
Verifies energy analytics, battery analytics, risk management, cost comparison,
and Flask JSON API endpoints.
"""

import pytest
import json
from app import create_app
from services import (
    EnergyAnalyticsService,
    RiskAnalyticsService,
    BatteryAnalyticsService,
    CostAnalysisService,
)


@pytest.fixture
def app():
    """Create Flask application test instance."""
    app_instance = create_app("testing")
    yield app_instance


@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()


class TestEnergyAnalyticsService:
    """Validates campus-level energy balance, totals, asset utilization, and chart series."""

    def test_energy_metrics_structure(self):
        metrics = EnergyAnalyticsService.get_energy_metrics()
        assert metrics["status"] == "VALIDATED_ACTUAL_OUTPUT"
        assert metrics["is_synthetic_data"] is True
        assert "SYNTHETIC SIMULATION DATA" in metrics["data_label"]

        totals = metrics["totals"]
        assert totals["total_demand_kwh"] > 0
        assert totals["total_solar_kwh"] > 0
        assert totals["total_day_ahead_kwh"] > 0
        assert totals["total_real_time_kwh"] > 0

        ratios = metrics["ratios"]
        assert ratios["solar_utilization_pct"] >= 0.0
        assert ratios["grid_dependency_pct"] >= 0.0
        assert ratios["battery_utilization_pct"] >= 0.0

        charts = metrics["charts"]
        assert len(charts["hours"]) == 24
        assert len(charts["campus_demand_kw"]) == 24
        assert len(charts["solar_generation_kw"]) == 24
        assert len(charts["day_ahead_procurement_kw"]) == 24


class TestRiskAnalyticsService:
    """Validates tail risk metrics, VaR/CVaR quantiles, and Pareto frontier."""

    def test_risk_metrics_structure(self):
        risk = RiskAnalyticsService.get_risk_metrics()
        assert risk["status"] == "VALIDATED_ACTUAL_OUTPUT"

        m = risk["metrics"]
        assert m["expected_cost_inr"] > 0
        assert m["var_90_inr"] <= m["var_95_inr"] <= m["var_99_inr"]
        assert m["var_95_inr"] <= m["cvar_95_inr"]
        assert m["std_scenario_cost_inr"] > 0

        # Weather exposure breakdown
        assert "weather_exposure" in risk
        assert len(risk["weather_exposure"]) > 0

        # Histogram bins
        assert len(risk["histogram"]) > 0

        # Pareto frontier
        frontier = risk["pareto_frontier"]
        assert len(frontier) >= 5
        for pt in frontier:
            assert "lambda" in pt
            assert "expected_cost_inr" in pt
            assert "cvar_95_inr" in pt

    def test_pareto_frontier_convexity(self):
        frontier = RiskAnalyticsService.evaluate_risk_aversion_frontier()
        assert len(frontier) == 5

        # As lambda increases, CVaR should not increase (risk decreases or remains equal)
        for i in range(len(frontier) - 1):
            assert frontier[i]["cvar_95_inr"] >= frontier[i + 1]["cvar_95_inr"] - 0.01


class TestBatteryAnalyticsService:
    """Validates BESS SoC conservation, cycling degradation, and physical feasibility."""

    def test_battery_analytics(self):
        batt = BatteryAnalyticsService.get_battery_analytics()
        assert batt["status"] == "VALIDATED_ACTUAL_OUTPUT"

        params = batt["parameters"]
        assert params["capacity_kwh"] == 1000.0
        assert params["max_charge_kw"] == 400.0
        assert params["max_discharge_kw"] == 400.0

        throughput = batt["energy_throughput"]
        assert throughput["charging_energy_kwh"] > 0
        assert throughput["discharging_energy_kwh"] > 0
        assert throughput["efficiency_losses_kwh"] >= 0

        soc_sum = batt["soc_summary"]
        assert soc_sum["initial_soc_kwh"] == 500.0
        assert soc_sum["terminal_neutrality_satisfied"] is True

        charts = batt["charts"]
        assert len(charts["hours"]) == 24
        assert len(charts["soc_pct"]) == 24
        assert len(charts["charge_kw"]) == 24
        assert len(charts["discharge_kw"]) == 24


class TestCostAnalysisService:
    """Validates stochastic vs deterministic economics, VSS, and EVPI."""

    def test_cost_comparison(self):
        cost = CostAnalysisService.get_cost_comparison()
        assert cost["status"] == "VALIDATED_ACTUAL_OUTPUT"

        summary = cost["summary"]
        assert summary["stochastic_policy_cost_inr"] > 0
        assert summary["deterministic_policy_cost_inr"] > summary["stochastic_policy_cost_inr"]
        assert summary["vss_inr"] > 0
        assert summary["percentage_savings"] > 0
        assert summary["evpi_inr"] > 0

        # TOU breakdown
        tou = cost["tou_breakdown"]
        assert len(tou) == 3
        for win_name, win_data in tou.items():
            assert "hours" in win_data
            assert "stochastic_spend_inr" in win_data
            assert "deterministic_spend_inr" in win_data
            assert win_data["stochastic_spend_inr"] > 0

        # Hourly charts
        charts = cost["charts"]
        assert len(charts["hours"]) == 24
        assert len(charts["hourly_savings_inr"]) == 24


class TestAnalyticsApiRoutes:
    """Validates HTTP API endpoints under /api/analytics."""

    def test_api_analytics_energy(self, client):
        resp = client.get("/api/analytics/energy")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "VALIDATED_ACTUAL_OUTPUT"
        assert "totals" in data
        assert "ratios" in data

    def test_api_analytics_battery(self, client):
        resp = client.get("/api/analytics/battery")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "VALIDATED_ACTUAL_OUTPUT"
        assert "soc_summary" in data
        assert "energy_throughput" in data

    def test_api_analytics_risk(self, client):
        resp = client.get("/api/analytics/risk")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "VALIDATED_ACTUAL_OUTPUT"
        assert "metrics" in data
        assert "pareto_frontier" in data

    def test_api_analytics_cost(self, client):
        resp = client.get("/api/analytics/cost")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "VALIDATED_ACTUAL_OUTPUT"
        assert "summary" in data
        assert "tou_breakdown" in data

    def test_api_analytics_sensitivity(self, client):
        resp = client.get("/api/analytics/sensitivity")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "SUCCESS"
        assert "sensitivity_results" in data

    def test_api_analytics_risk_aversion_post(self, client):
        resp = client.post(
            "/api/analytics/risk-aversion",
            data=json.dumps({"lambda_values": [0.0, 0.5, 1.0]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "SUCCESS"
        assert "frontier" in data
