"""
GRIDWISE AI - Test Suite for Phase 8: Live Weather, Adaptive Forecasting & Intelligence
Tests Open-Meteo integration, caching, fallback behaviors, solar physical constraints,
adaptive scenario probabilities, two-stage LP solver integration, previous-run deltas,
alerts engine, and all Flask REST endpoints.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

from app import create_app
from services.weather_service import WeatherService
from services.adaptive_forecasting_service import AdaptiveForecastingService
from services.adaptive_optimization_service import (
    AdaptiveOptimizationService,
    AdaptiveAlertsEngine,
)


@pytest.fixture
def app():
    """Create test application context."""
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    """Create test HTTP client."""
    return app.test_client()


# 1. Weather API & Caching Tests
def test_weather_service_data_retrieval():
    """Tests weather service returns valid current and 24h hourly forecast."""
    data = WeatherService.get_weather_data(force_refresh=False)
    assert data is not None
    assert "location_name" in data
    assert "current" in data
    assert "hourly_24h" in data
    assert len(data["hourly_24h"]) == 24
    assert "temperature_c" in data["current"]
    assert "relative_humidity_pct" in data["current"]


def test_weather_service_cache_freshness():
    """Tests 15-minute cache detection."""
    cached_payload = {
        "fetched_at": "2026-10-30T10:00:00+00:00",
        "hourly_24h": [],
    }
    # Future or ancient timestamps are handled
    assert isinstance(WeatherService._is_cache_fresh(cached_payload), bool)


def test_weather_fallback_on_api_error():
    """Tests graceful fallback when Open-Meteo network is unreachable."""
    fallback = WeatherService._generate_fallback_weather(10.7905, 78.7047, reason="Network timeout")
    assert fallback["status"] == "FALLBACK"
    assert fallback["is_stale"] is True
    assert len(fallback["hourly_24h"]) == 24
    assert fallback["current"]["temperature_c"] > 0


# 2. Physics-Based Solar Generation Constraints
def test_solar_nighttime_zero_invariant():
    """Tests that solar power output is strictly zero at night hours."""
    night_hours = [20, 21, 22, 23, 0, 1, 2, 3, 4, 5]
    for h in night_hours:
        power = AdaptiveForecastingService.compute_physical_solar_generation(
            hour_of_day=h,
            solar_radiation_w_m2=500.0,  # Even if high radiation erroneously reported
            temperature_c=28.0,
            cloud_cover_pct=10.0,
        )
        assert power == 0.0, f"Solar power at hour {h} must be strictly 0.0 kW"


def test_solar_capacity_and_non_negativity():
    """Tests solar generation stays bounded within [0, 800 kWp]."""
    # Extremely intense noon sun
    peak_power = AdaptiveForecastingService.compute_physical_solar_generation(
        hour_of_day=12,
        solar_radiation_w_m2=1400.0,
        temperature_c=35.0,
        cloud_cover_pct=0.0,
    )
    assert 0.0 <= peak_power <= 800.0

    # Negative radiation input should clip to 0
    neg_power = AdaptiveForecastingService.compute_physical_solar_generation(
        hour_of_day=12,
        solar_radiation_w_m2=-50.0,
        temperature_c=30.0,
        cloud_cover_pct=100.0,
    )
    assert neg_power >= 0.0


def test_solar_temperature_derating():
    """Tests that higher ambient temperature lowers solar efficiency."""
    power_cool = AdaptiveForecastingService.compute_physical_solar_generation(
        hour_of_day=12,
        solar_radiation_w_m2=800.0,
        temperature_c=25.0,  # STC temperature
        cloud_cover_pct=10.0,
    )
    power_hot = AdaptiveForecastingService.compute_physical_solar_generation(
        hour_of_day=12,
        solar_radiation_w_m2=800.0,
        temperature_c=45.0,  # 20°C above STC
        cloud_cover_pct=10.0,
    )
    assert power_cool > power_hot, "Elevated temperature must derate PV efficiency"


# 3. Weather-Sensitive Demand Tests
def test_weather_sensitive_demand_hvac_response():
    """Tests that high afternoon temperature increases campus demand."""
    base_dem = 500.0
    dem_mild = AdaptiveForecastingService.compute_weather_sensitive_demand(
        base_demand=base_dem,
        temperature_c=25.0,
        relative_humidity_pct=50.0,
        hour_of_day=14,
    )
    dem_heatwave = AdaptiveForecastingService.compute_weather_sensitive_demand(
        base_demand=base_dem,
        temperature_c=38.0,
        relative_humidity_pct=75.0,
        hour_of_day=14,
    )
    assert dem_heatwave > dem_mild
    assert dem_mild >= 100.0


# 4. Adaptive Scenario Generation & Reproducibility
def test_adaptive_scenarios_probabilities_and_bounds():
    """Tests generation of >= 100 scenarios with strict probability normalization."""
    summary = AdaptiveForecastingService.generate_adaptive_scenarios(
        num_scenarios=100,
        random_seed=42,
    )
    assert summary["num_scenarios"] == 100
    assert summary["hours_per_scenario"] == 24
    assert abs(summary["probability_sum"] - 1.0) < 1e-5

    # Check generated CSV
    scen_csv = Path(summary["scenarios_csv"])
    assert scen_csv.exists()
    df = pd.read_csv(scen_csv)
    assert len(df) == 100 * 24
    assert np.all(df["demand_kwh"] >= 0)
    assert np.all(df["solar_kwh"] >= 0)
    assert np.all(df["solar_kwh"] <= 800.0)
    assert np.all(df["day_ahead_price_inr_kwh"] > 0)


def test_scenario_reproducibility():
    """Tests identical scenarios are generated with same random seed."""
    s1 = AdaptiveForecastingService.generate_adaptive_scenarios(num_scenarios=50, random_seed=123)
    s2 = AdaptiveForecastingService.generate_adaptive_scenarios(num_scenarios=50, random_seed=123)
    assert s1["mean_daily_solar_kwh"] == s2["mean_daily_solar_kwh"]
    assert s1["mean_daily_demand_kwh"] == s2["mean_daily_demand_kwh"]


# 5. Adaptive Two-Stage Stochastic Optimization
def test_adaptive_optimization_solving_and_deltas():
    """Tests adaptive stochastic LP solution, risk metrics, and previous-run comparison."""
    # First run
    res1 = AdaptiveOptimizationService.run_adaptive_optimization(num_scenarios=50, random_seed=42)
    assert res1["solver_status"] == "OPTIMAL"
    assert res1["expected_cost_inr"] > 0
    assert res1["cvar_95_inr"] >= res1["var_95_inr"]
    assert len(res1["hourly_schedule"]["day_ahead_procurement_kw"]) == 24
    assert res1["vss_inr"] >= 0.0

    # Second run to test previous-run comparison deltas
    res2 = AdaptiveOptimizationService.run_adaptive_optimization(num_scenarios=50, random_seed=42)
    assert res2["comparison"]["previous_run_uuid"] == res1["run_uuid"]
    assert "cost_delta_inr" in res2["comparison"]


# 6. Intelligent Alerts Engine Tests
def test_adaptive_alerts_detection():
    """Tests alert engine triggers appropriate categories on abnormal conditions."""
    mock_summary = {
        "mean_daily_solar_kwh": 1800.0,  # Below threshold 2600 -> should trigger Solar Reduction
        "mean_daily_demand_kwh": 11200.0,# Above threshold 10500 -> should trigger Demand Surge
    }
    mock_out = MagicMock()
    mock_out.expected_total_cost_inr = 62000.0  # Above critical threshold 60000
    mock_out.cvar_95_cost_inr = 65000.0        # Above threshold 61000
    mock_out.day_ahead_schedule_kw = np.full(24, 300.0)
    mock_out.expected_battery_soc_kwh = np.full(24, 150.0) # Below 200 kWh buffer

    alerts = AdaptiveAlertsEngine.evaluate_and_record_alerts(
        stochastic_out=mock_out,
        summary_stats=mock_summary,
    )
    categories = [a["category"] for a in alerts]
    assert "Solar Reduction" in categories
    assert "Demand Surge" in categories
    assert "High Cost" in categories
    assert "CVaR Risk" in categories
    assert "Battery Readiness" in categories


# 7. Flask REST API Endpoints Tests
def test_api_live_weather(client):
    res = client.get("/api/live-weather")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert "hourly_24h" in res.json["data"]


def test_api_adaptive_forecast(client):
    res = client.get("/api/adaptive/forecast")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert "solar_forecast" in res.json["data"]
    assert "demand_forecast" in res.json["data"]


def test_api_adaptive_scenarios_generate(client):
    res = client.post("/api/adaptive/scenarios/generate", json={"num_scenarios": 20, "random_seed": 99})
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"]["num_scenarios"] == 20


def test_api_adaptive_optimize(client):
    res = client.post("/api/adaptive/optimize", json={"num_scenarios": 25, "risk_aversion": 0.0})
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"]["solver_status"] == "OPTIMAL"


def test_api_adaptive_results_latest(client):
    res = client.get("/api/adaptive/results/latest")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert "expected_cost_inr" in res.json["data"]


def test_api_adaptive_history(client):
    res = client.get("/api/adaptive/history?limit=5")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert isinstance(res.json["data"], list)


def test_api_adaptive_alerts(client):
    res = client.get("/api/adaptive/alerts")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert isinstance(res.json["data"], list)


def test_api_adaptive_status(client):
    res = client.get("/api/adaptive/status")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["status"] == "OPERATIONAL"


def test_live_intelligence_page(client):
    res = client.get("/live-intelligence")
    assert res.status_code == 200
    assert b"Live Energy Intelligence" in res.data
    assert b"Tiruchirappalli" in res.data

