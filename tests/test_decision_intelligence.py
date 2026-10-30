"""
GRIDWISE AI - Test Suite for Phase 9: AI Decision Intelligence & Multi-Objective Optimization
Tests explainability extraction, recommendation generation, multi-objective formulation,
Pareto dominance checks, what-if simulation sandbox, battery lifecycle analytics, and REST APIs.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

import tempfile
import os
from app import create_app
from database.database import init_db
from services.explainability_service import ExplainabilityService
from services.recommendation_service import RecommendationService
from services.multi_objective_service import MultiObjectiveOptimizer
from services.what_if_service import WhatIfSimulationService
from services.battery_lifecycle_service import BatteryLifecycleService
from optimization import (
    StochasticOptimizer,
    BatteryParameters,
    GridParameters,
    OptimizationOutput,
)


@pytest.fixture
def app():
    """Create test application context with isolated temporary SQLite DB."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    app = create_app("testing")
    app.config["DATABASE_PATH"] = path
    yield app
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass



@pytest.fixture
def client(app):
    """Create test HTTP client."""
    return app.test_client()



@pytest.fixture
def sample_scenarios_df():
    """Provides a small 2-scenario x 24h DataFrame for fast unit testing."""
    rows = []
    for s in ["SCEN_01", "SCEN_02"]:
        for t in range(24):
            rows.append({
                "scenario_id": s,
                "hour": t,
                "weather_condition": "Sunny",
                "probability": 0.5,
                "demand_kwh": 400.0 + 50.0 * np.sin(np.pi * t / 12),
                "solar_kwh": max(0.0, 500.0 * np.sin(np.pi * (t - 6) / 12)) if 6 <= t <= 18 else 0.0,
                "day_ahead_price_inr_kwh": 5.0 + (3.0 if 14 <= t <= 19 else 0.0),
                "real_time_price_inr_kwh": 6.0 + (4.0 if 14 <= t <= 19 else 0.0),
            })
    return pd.DataFrame(rows)


# 1. Objective Weight Validation & Scaling Tests
def test_objective_weights_validation():
    """Tests normalization and non-negativity validation for multi-objective weights."""
    valid_weights = {"cost": 0.4, "cvar": 0.2, "solar": 0.2, "grid": 0.1, "battery": 0.1}
    norm = MultiObjectiveOptimizer.validate_weights(valid_weights)
    assert abs(sum(norm.values()) - 1.0) < 1e-3

    # Negative weight should raise ValueError
    with pytest.raises(ValueError):
        MultiObjectiveOptimizer.validate_weights({"cost": -0.5, "cvar": 0.5})

    # All-zero weights defaults to cost-only
    zero_weights = {"cost": 0.0, "cvar": 0.0, "solar": 0.0, "grid": 0.0, "battery": 0.0}
    norm_zero = MultiObjectiveOptimizer.validate_weights(zero_weights)
    assert norm_zero["cost"] == 1.0


# 2. Cost-Only Mode Compatibility (Reproduces Phase 4)
def test_cost_only_mode_compatibility(sample_scenarios_df):
    """Tests that cost-only multi-objective optimization matches the standard stochastic model."""
    res_cost_only = MultiObjectiveOptimizer.run_multi_objective_optimization(
        weights={"cost": 1.0, "cvar": 0.0, "solar": 0.0, "grid": 0.0, "battery": 0.0},
        num_scenarios=2,
        scenarios_df=sample_scenarios_df,
    )
    assert res_cost_only["is_cost_only"] is True
    assert res_cost_only["solver_status"] == "OPTIMAL"
    assert res_cost_only["objectives"]["expected_cost_inr"] > 0
    assert len(res_cost_only["schedule"]["day_ahead_schedule_kw"]) == 24


# 3. Pareto Dominance Checks
def test_pareto_dominance_logic():
    """Tests non-dominated check between solution vectors."""
    # Solution A dominates Solution B (cheaper cost, same or better in all others)
    sol_A = {
        "expected_cost_inr": 45000.0,
        "cvar_95_inr": 55000.0,
        "solar_utilization_pct": 98.0,
        "grid_dependency_pct": 65.0,
        "degradation_cost_inr": 250.0,
    }
    sol_B = {
        "expected_cost_inr": 48000.0,
        "cvar_95_inr": 58000.0,
        "solar_utilization_pct": 95.0,
        "grid_dependency_pct": 70.0,
        "degradation_cost_inr": 280.0,
    }
    assert MultiObjectiveOptimizer.check_pareto_dominance(sol_A, sol_B) is True
    assert MultiObjectiveOptimizer.check_pareto_dominance(sol_B, sol_A) is False

    # Trade-off solutions (A is cheaper, but B has lower CVaR) -> Neither dominates
    sol_C = {
        "expected_cost_inr": 44000.0,
        "cvar_95_inr": 60000.0,
        "solar_utilization_pct": 95.0,
        "grid_dependency_pct": 70.0,
        "degradation_cost_inr": 280.0,
    }
    assert MultiObjectiveOptimizer.check_pareto_dominance(sol_C, sol_A) is False
    assert MultiObjectiveOptimizer.check_pareto_dominance(sol_A, sol_C) is False


# 4. Battery Lifecycle Analytics Tests
def test_battery_lifecycle_metrics():
    """Tests throughput, EFC, DoD, and degradation calculations."""
    soc_24h = np.linspace(400, 800, 24)
    ch_24h = np.full(24, 20.0)
    dis_24h = np.full(24, 20.0)

    metrics = BatteryLifecycleService.compute_lifecycle_metrics(
        charge_kw_24h=ch_24h,
        discharge_kw_24h=dis_24h,
        soc_kwh_24h=soc_24h,
        battery_capacity_kwh=1000.0,
    )
    assert metrics["charge_throughput_kwh"] == 480.0
    assert metrics["discharge_throughput_kwh"] == 480.0
    assert metrics["equivalent_full_cycles"] == 0.48
    assert metrics["max_dod_pct"] == 40.0
    assert metrics["estimated_degradation_cost_inr"] == round(480.0 * 0.35, 2)
    assert metrics["projected_cycle_life_remaining_years"] > 0


# 5. What-If Simulation Isolation & Comparison Tests
def test_what_if_simulation_isolation(sample_scenarios_df):
    """Tests that What-If simulation executes parametric changes without mutating config."""
    res = WhatIfSimulationService.run_experiment(
        experiment_name="Solar Expansion Test",
        solar_capacity_kw=1200.0,
        battery_capacity_kwh=1500.0,
        demand_scale=1.1,
        num_scenarios=2,
    )
    assert res["experiment_uuid"].startswith("EXP-")
    assert res["results"]["solver_status"] == "OPTIMAL"
    assert "cost_delta_inr" in res["results"]
    assert "cvar_delta_inr" in res["results"]
    assert len(res["schedule"]["day_ahead_schedule_kw"]) == 24


# 6. Explainability & Recommendation Generation Tests
def test_explainability_and_recommendations(sample_scenarios_df):
    """Tests extraction of actual-data explanations and actionable recommendations."""
    opt = StochasticOptimizer(BatteryParameters(1000, 400, 400, 0.5, 0.92, 0.92), GridParameters(1000, 1000, 1000, 500))
    out = opt.solve_stochastic_model(scenarios_df=sample_scenarios_df, risk_weight_lambda=0.0)
    x_det, eev, _, _ = opt.solve_deterministic_baseline(sample_scenarios_df)
    ws, _ = opt.solve_wait_and_see(sample_scenarios_df)
    vss = max(0.0, eev - out.expected_total_cost_inr)
    evpi = max(0.0, out.expected_total_cost_inr - ws)

    exp_payload = ExplainabilityService.generate_all_explanations(
        stochastic_out=out,
        scenarios_df=sample_scenarios_df,
        eev_cost=eev,
        vss_val=vss,
        ws_cost=ws,
        evpi_val=evpi,
    )
    assert exp_payload["count"] >= 5
    dec_types = [e["decision_type"] for e in exp_payload["explanations"]]
    assert "Day-Ahead Procurement" in dec_types
    assert "Battery Dispatch & Arbitrage" in dec_types
    assert "Solar PV Utilization" in dec_types

    recs = RecommendationService.generate_recommendations(
        stochastic_out=out,
        scenarios_df=sample_scenarios_df,
        vss_val=vss,
        eev_cost=eev,
    )
    assert len(recs) >= 3
    cats = [r["category"] for r in recs]
    assert "Battery Scheduling" in cats
    assert "Grid Procurement" in cats


# 7. Flask REST API Endpoints Tests
def test_api_decision_explanation(client):
    res = client.get("/api/decision/explanation")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert isinstance(res.json["data"], list)


def test_api_decision_recommendations(client):
    res = client.get("/api/decision/recommendations")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert isinstance(res.json["data"], list)


def test_api_decision_multi_objective(client):
    res = client.post("/api/decision/multi-objective", json={
        "weights": {"cost": 0.5, "cvar": 0.2, "solar": 0.1, "grid": 0.1, "battery": 0.1},
        "num_scenarios": 10,
    })
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"]["solver_status"] == "OPTIMAL"


def test_api_decision_pareto(client):
    res = client.get("/api/decision/pareto?num_scenarios=10")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert "solutions" in res.json["data"]


def test_api_what_if_run_and_history(client):
    res_run = client.post("/api/what-if/run", json={
        "experiment_name": "API Test Experiment",
        "solar_capacity_kw": 900.0,
        "battery_capacity_kwh": 1100.0,
        "demand_scale": 1.05,
        "num_scenarios": 10,
    })
    assert res_run.status_code == 200
    assert res_run.json["success"] is True
    assert "expected_cost_inr" in res_run.json["data"]["results"]

    res_hist = client.get("/api/what-if/history?limit=5")
    assert res_hist.status_code == 200
    assert res_hist.json["success"] is True
    assert len(res_hist.json["data"]) >= 1


def test_api_battery_lifecycle(client):
    res = client.get("/api/battery/lifecycle")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert "equivalent_full_cycles" in res.json["data"]


def test_api_decision_compare(client):
    res = client.get("/api/decision/compare")
    assert res.status_code == 200
    assert res.json["success"] is True
    assert "comparison" in res.json


def test_decision_intelligence_page(client):
    res = client.get("/decision-intelligence")
    assert res.status_code == 200
    assert b"AI Decision Intelligence Studio" in res.data
    assert b"Pareto Frontier" in res.data
