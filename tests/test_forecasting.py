"""
GRIDWISE AI - Test Suite for Intelligent Energy Forecasting Engine
Tests feature engineering, deterministic and probabilistic metrics, individual forecasters,
physical domain constraints, scenario generation, optimization service, and Flask routes.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from app import create_app
from forecasting.feature_engineering import (
    build_demand_features,
    build_solar_features,
    build_price_features,
    chronological_split,
)
from forecasting.evaluation import compute_metrics, compute_interval_metrics
from forecasting.prediction_intervals import PredictionIntervalEstimator
from forecasting.demand_forecaster import CampusDemandForecaster
from forecasting.solar_forecaster import SolarGenerationForecaster
from forecasting.price_forecaster import ElectricityPriceForecaster
from forecasting.uncertainty_estimator import ForecastUncertaintyEstimator
from services.forecast_optimization_service import ForecastOptimizationService


@pytest.fixture
def app():
    """Create test application context."""
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_demand_df():
    """Generates synthetic hourly demand series for testing."""
    dates = pd.date_range("2024-01-01", periods=1000, freq="h")
    np.random.seed(42)
    # 24h periodic demand with noise
    hour = dates.hour.values
    base_dem = 400.0 + 200.0 * np.sin(2 * np.pi * (hour - 6) / 24) + np.random.normal(0, 15, len(dates))
    return pd.DataFrame({
        "timestamp": dates,
        "actual_demand_kwh": np.maximum(100.0, base_dem),
    })


@pytest.fixture
def sample_solar_df():
    """Generates synthetic hourly solar series for testing."""
    dates = pd.date_range("2024-01-01", periods=1000, freq="h")
    np.random.seed(42)
    hour = dates.hour.values
    solar = np.zeros(len(dates))
    day_mask = (hour >= 6) & (hour <= 19)
    solar[day_mask] = 500.0 * np.sin(np.pi * (hour[day_mask] - 6) / 13) + np.random.normal(0, 20, np.sum(day_mask))
    solar = np.clip(solar, 0.0, 800.0)
    return pd.DataFrame({
        "timestamp": dates,
        "solar_generation_kwh": solar,
    })


@pytest.fixture
def sample_price_df():
    """Generates synthetic hourly prices for testing."""
    dates = pd.date_range("2024-01-01", periods=1000, freq="h")
    np.random.seed(42)
    hour = dates.hour.values
    base_price = 5.0 + 3.0 * ((hour >= 9) & (hour <= 21)).astype(float)
    return pd.DataFrame({
        "timestamp": dates,
        "day_ahead_price_inr_kwh": base_price + np.random.normal(0, 0.2, len(dates)),
        "real_time_price_inr_kwh": base_price + np.random.normal(0, 0.8, len(dates)),
    })


# 1. Feature Engineering Tests
def test_feature_engineering_lags_and_split(sample_demand_df):
    feat_df = build_demand_features(sample_demand_df)
    assert not feat_df.empty
    assert "demand_lag_1" in feat_df.columns
    assert "demand_lag_24" in feat_df.columns
    assert "hour_sin" in feat_df.columns
    assert "demand_rolling_mean_24" in feat_df.columns

    # Chronological Split
    train_df, val_df, test_df = chronological_split(feat_df, train_ratio=0.70, val_ratio=0.15)
    total_len = len(train_df) + len(val_df) + len(test_df)
    assert total_len == len(feat_df)
    assert len(train_df) > len(val_df)
    assert len(val_df) == len(test_df)


# 2. Evaluation Metric Calculation Tests
def test_evaluation_metrics_deterministic():
    y_true = np.array([100.0, 200.0, 300.0, 400.0])
    y_pred = np.array([110.0, 190.0, 310.0, 390.0])
    metrics = compute_metrics(y_true, y_pred)
    assert metrics["mae"] == 10.0
    assert metrics["rmse"] == 10.0
    assert metrics["r2_score"] > 0.95
    assert metrics["wape_pct"] == 4.0


def test_evaluation_metrics_probabilistic():
    y_true = np.array([100.0, 200.0, 300.0, 400.0])
    y_lower = np.array([90.0, 180.0, 290.0, 380.0])
    y_upper = np.array([110.0, 220.0, 310.0, 420.0])
    int_metrics = compute_interval_metrics(y_true, y_lower, y_upper)
    assert int_metrics["picp_coverage_pct"] == 100.0
    assert int_metrics["pinaw_width_pct"] > 0.0


# 3. Prediction Intervals Estimator
def test_prediction_interval_estimator():
    y_true = np.random.normal(100, 10, 200)
    y_pred = np.random.normal(100, 10, 200)
    hours = np.tile(np.arange(24), 9)[:200]

    pie = PredictionIntervalEstimator(confidence_level=0.90)
    pie.fit(y_true, y_pred, hours=hours)

    test_pred = np.array([100.0, 150.0, 200.0])
    low, high = pie.predict_intervals(test_pred, hours=np.array([1, 2, 3]), min_clip=0.0)
    assert len(low) == 3
    assert len(high) == 3
    assert np.all(low <= high)
    assert np.all(low >= 0.0)


# 4. Solar Physical Domain Constraints
def test_solar_physical_constraints():
    raw_preds = np.array([-15.0, 10.0, 450.0, 950.0])
    hours = np.array([2, 22, 12, 13])  # Hours 2 and 22 are night hours
    clipped = SolarGenerationForecaster.enforce_physical_constraints(raw_preds, hours=hours, max_capacity=800.0)

    # Night hours strictly 0
    assert clipped[0] == 0.0
    assert clipped[1] == 0.0
    # Day hour within bounds
    assert clipped[2] == 450.0
    # Day hour capped at capacity
    assert clipped[3] == 800.0


# 5. Model Training & Next 24h Predictions
def test_demand_forecaster_fit_and_predict(sample_demand_df):
    forecaster = CampusDemandForecaster(random_state=42)
    eval_res = forecaster.train_and_evaluate(sample_demand_df)
    assert "selected_model" in eval_res
    assert "test_metrics" in eval_res

    pred_24h = forecaster.predict_next_24h(sample_demand_df)
    assert len(pred_24h) == 24
    assert "predicted_demand_kwh" in pred_24h.columns
    assert "demand_ci_lower_kwh" in pred_24h.columns
    assert "demand_ci_upper_kwh" in pred_24h.columns
    assert np.all(pred_24h["demand_ci_lower_kwh"] <= pred_24h["demand_ci_upper_kwh"])


def test_solar_forecaster_fit_and_predict(sample_solar_df):
    forecaster = SolarGenerationForecaster(random_state=42)
    eval_res = forecaster.train_and_evaluate(sample_solar_df)
    assert "selected_model" in eval_res

    pred_24h = forecaster.predict_next_24h(sample_solar_df)
    assert len(pred_24h) == 24
    assert np.all(pred_24h["predicted_solar_kwh"] >= 0.0)
    assert np.all(pred_24h["predicted_solar_kwh"] <= 800.0)

    # Night hours check
    for h in SolarGenerationForecaster.NIGHT_HOURS:
        assert pred_24h.loc[pred_24h["hour"] == h, "predicted_solar_kwh"].iloc[0] == 0.0


# 6. Forecast Scenarios & Probability Normalization
def test_forecast_scenarios_generation(sample_demand_df, sample_solar_df, sample_price_df):
    estimator = ForecastUncertaintyEstimator(random_seed=42)
    estimator.fit_all_models(sample_demand_df, sample_solar_df, sample_price_df)
    res = estimator.generate_forecasts_and_scenarios(
        sample_demand_df, sample_solar_df, sample_price_df, num_scenarios=20
    )
    assert res["status"] == "SUCCESS"
    assert res["num_scenarios_generated"] == 20
    assert abs(res["probability_sum"] - 1.0) < 1e-5


# 7. Forecast-Driven Stochastic Optimization
def test_forecast_optimization_service():
    res = ForecastOptimizationService.run_forecast_optimization(num_scenarios=25)
    assert res["solver_status"] == "OPTIMAL"
    assert res["expected_total_cost_inr"] > 0
    assert len(res["day_ahead_schedule_kw"]) == 24
    assert res["vss_inr"] >= 0.0
    assert res["evpi_inr"] >= 0.0


# 8. Web Route & API Endpoints Tests
def test_forecasting_page_route(client):
    response = client.get("/forecasting")
    assert response.status_code == 200
    assert b"Intelligent Microgrid Forecasting" in response.data
    assert b"SYNTHETIC SIMULATION DATA" in response.data


def test_api_forecast_endpoints(client):
    r_dem = client.get("/api/forecast/demand")
    assert r_dem.status_code == 200
    assert r_dem.json["success"] is True
    assert len(r_dem.json["data"]) == 24

    r_sol = client.get("/api/forecast/solar")
    assert r_sol.status_code == 200
    assert r_sol.json["success"] is True
    assert len(r_sol.json["data"]) == 24

    r_pri = client.get("/api/forecast/prices")
    assert r_pri.status_code == 200
    assert r_pri.json["success"] is True
    assert len(r_pri.json["data"]) == 24

    r_eval = client.get("/api/forecast/evaluation")
    assert r_eval.status_code == 200
    assert r_eval.json["success"] is True

    r_opt = client.get("/api/forecast/optimization-results")
    assert r_opt.status_code == 200
    assert r_opt.json["success"] is True
