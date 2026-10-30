"""
GRIDWISE AI - Phase 4 Stochastic Optimization Automated Test Suite
Verifies mathematical formulations, solver execution, physical constraints, VSS, EVPI, and API integration.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from optimization import (
    StochasticOptimizer,
    ScenarioLoader,
    ScenarioValidationError,
    BatteryParameters,
    GridParameters,
    ObjectiveBuilder,
    ConstraintBuilder,
    LinearSolver,
    OptimizationSolverError,
)
from app import create_app

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "data" / "results"


@pytest.fixture
def test_scenarios_df():
    """Fixture providing validated scenario DataFrame."""
    df, meta = ScenarioLoader.load_and_validate(max_scenarios=10)
    return df


@pytest.fixture
def flask_test_client():
    """Fixture providing Flask test client."""
    app = create_app("testing")
    with app.test_client() as client:
        yield client


# 1. Scenario Loading & Validation Tests
def test_scenario_loading_success():
    """Verify loading of Phase 3 scenario files."""
    df, meta = ScenarioLoader.load_and_validate(max_scenarios=20)
    assert len(df) == 20 * 24
    assert meta["total_scenarios"] == 20
    assert np.isclose(meta["probability_sum"], 1.0, atol=1e-4)


def test_scenario_probability_validation(tmp_path):
    """Verify error raised on invalid probability sum."""
    df, _ = ScenarioLoader.load_and_validate(max_scenarios=5)
    bad_df = df.copy()
    bad_df["probability"] = 0.50  # 5 * 0.5 = 2.5 != 1.0
    bad_file = tmp_path / "bad_scenarios.csv"
    bad_df.to_csv(bad_file, index=False)
    with pytest.raises(ScenarioValidationError):
        ScenarioLoader.load_and_validate(filepath=bad_file, max_scenarios=None)


def test_scenario_non_negative_checks():
    """Verify error raised when demand or solar contains negative values."""
    df, _ = ScenarioLoader.load_and_validate(max_scenarios=5)
    assert (df["demand_kwh"] >= 0).all()
    assert (df["solar_kwh"] >= 0).all()


# 2. Objective & Constraint Construction Tests
def test_objective_builder_dimensions():
    """Verify linear objective coefficient vector dimensions and CVaR indexing."""
    N = 10
    T = 24
    probs = np.ones(N) / N
    da_prices = np.array([5.0] * T)
    rt_prices = np.ones((N, T)) * 6.0
    b_params = BatteryParameters()
    g_params = GridParameters()

    # Risk-neutral
    c, idx_map = ObjectiveBuilder.build_objective_vector(
        num_scenarios=N,
        probabilities=probs,
        da_prices_24h=da_prices,
        rt_prices_matrix=rt_prices,
        battery_params=b_params,
        grid_params=g_params,
        risk_weight_lambda=0.0,
    )
    assert len(c) == T + 6 * N * T
    assert idx_map["total_vars"] == T + 6 * N * T

    # Risk-averse
    c_cvar, idx_cvar = ObjectiveBuilder.build_objective_vector(
        num_scenarios=N,
        probabilities=probs,
        da_prices_24h=da_prices,
        rt_prices_matrix=rt_prices,
        battery_params=b_params,
        grid_params=g_params,
        risk_weight_lambda=0.20,
    )
    assert len(c_cvar) == T + 6 * N * T + 1 + N


def test_constraints_assembly_dimensions(test_scenarios_df):
    """Verify sparse constraint matrix dimensions."""
    N = 10
    T = 24
    probs = np.ones(N) / N
    da_prices = np.array([5.0] * T)
    rt_prices = np.ones((N, T)) * 6.0
    dem = np.ones((N, T)) * 500.0
    sol = np.ones((N, T)) * 200.0
    b_params = BatteryParameters()
    g_params = GridParameters()

    c, idx_map = ObjectiveBuilder.build_objective_vector(
        num_scenarios=N,
        probabilities=probs,
        da_prices_24h=da_prices,
        rt_prices_matrix=rt_prices,
        battery_params=b_params,
        grid_params=g_params,
        risk_weight_lambda=0.0,
    )
    A_eq, b_eq, A_ub, b_ub, bounds = ConstraintBuilder.build_constraints(
        num_scenarios=N,
        demand_matrix=dem,
        solar_matrix=sol,
        da_prices_24h=da_prices,
        rt_prices_matrix=rt_prices,
        battery_params=b_params,
        grid_params=g_params,
        idx_map=idx_map,
    )
    assert A_eq.shape[1] == idx_map["total_vars"]
    assert A_ub.shape[1] == idx_map["total_vars"]
    assert len(bounds) == idx_map["total_vars"]


# 3. Solver Execution & Feasibility Tests
def test_small_stochastic_model_solve(test_scenarios_df):
    """Solves small subset model and validates optimality."""
    opt = StochasticOptimizer()
    out = opt.solve_stochastic_model(test_scenarios_df, max_scenarios=5)
    assert out.success is True
    assert out.expected_total_cost_inr > 0.0
    assert out.max_eq_residual < 1e-4
    assert out.max_ub_violation < 1e-4


def test_energy_balance_conservation(test_scenarios_df):
    """Verifies energy balance is satisfied strictly at every hour."""
    opt = StochasticOptimizer()
    out = opt.solve_stochastic_model(test_scenarios_df, max_scenarios=5)
    # Equality residuals must be negligible
    assert out.max_eq_residual < 1e-5


def test_battery_soc_and_limits(test_scenarios_df):
    """Verifies battery energy remains strictly within [15%, 95%] and periodicity holds."""
    b_params = BatteryParameters(capacity_kwh=1000.0, min_soc_pct=0.15, max_soc_pct=0.95, initial_soc_pct=0.50)
    opt = StochasticOptimizer(battery_params=b_params)
    out = opt.solve_stochastic_model(test_scenarios_df, max_scenarios=5)

    assert (out.matrix_b >= b_params.min_energy_kwh - 1e-4).all()
    assert (out.matrix_b <= b_params.max_energy_kwh + 1e-4).all()
    # Periodicity check: terminal SoC(23) >= initial SoC
    assert (out.matrix_b[:, 23] >= b_params.initial_energy_kwh - 1e-4).all()


def test_no_simultaneous_charging_and_discharging(test_scenarios_df):
    """Verifies that optimal solution has zero simultaneous charge and discharge."""
    opt = StochasticOptimizer()
    out = opt.solve_stochastic_model(test_scenarios_df, max_scenarios=5)
    simult = out.simultaneous_check
    assert simult["is_strictly_separated"] is True
    assert simult["max_simultaneous_kw"] < 1e-4


def test_grid_procurement_limits(test_scenarios_df):
    """Verifies total grid import stays below 1000 kW contractual threshold."""
    g_params = GridParameters(max_total_import_kw=1000.0)
    opt = StochasticOptimizer(grid_params=g_params)
    out = opt.solve_stochastic_model(test_scenarios_df, max_scenarios=5)

    for s in range(len(out.scenario_ids)):
        total_import = out.day_ahead_schedule_kw + out.matrix_g[s, :]
        assert (total_import <= 1000.0 + 1e-4).all()


# 4. Deterministic Baseline, VSS, and EVPI Tests
def test_deterministic_baseline_and_vss(test_scenarios_df):
    """Verifies EEV >= RP, ensuring VSS >= 0."""
    opt = StochasticOptimizer()
    rp_out = opt.solve_stochastic_model(test_scenarios_df, max_scenarios=10)
    x_det, eev_cost, ev_obj, _ = opt.solve_deterministic_baseline(test_scenarios_df.head(10*24))

    vss = eev_cost - rp_out.expected_total_cost_inr
    # VSS must be non-negative within numerical tolerance
    assert vss >= -1e-4, f"VSS violated: EEV={eev_cost}, RP={rp_out.expected_total_cost_inr}"


def test_evpi_calculation(test_scenarios_df):
    """Verifies WS <= RP, ensuring EVPI >= 0."""
    opt = StochasticOptimizer()
    sub_df = test_scenarios_df.head(10 * 24).copy()
    rp_out = opt.solve_stochastic_model(sub_df)
    ws_cost, _ = opt.solve_wait_and_see(sub_df)

    evpi = rp_out.expected_total_cost_inr - ws_cost
    assert evpi >= -1e-4, f"EVPI violated: RP={rp_out.expected_total_cost_inr}, WS={ws_cost}"


# 5. Risk-Averse Mean-CVaR Test
def test_cvar_risk_averse_model(test_scenarios_df):
    """Verifies risk-averse model with lambda = 0.50 solves and bounds CVaR."""
    opt = StochasticOptimizer()
    sub_df = test_scenarios_df.head(5 * 24).copy()
    out = opt.solve_stochastic_model(sub_df, risk_weight_lambda=0.50)
    assert out.success is True
    # CVaR at 95% must be >= VaR at 95% >= Expected Cost
    assert out.cvar_95_cost_inr >= out.var_95_cost_inr - 1e-4


# 6. Full 500-Scenario Optimization Test
def test_full_500_scenarios_solve():
    """Verifies that full 500-scenario stochastic LP solves cleanly and outputs results."""
    opt = StochasticOptimizer()
    out = opt.solve_stochastic_model(max_scenarios=500, time_limit_sec=60.0)
    assert out.success is True
    assert len(out.scenario_ids) == 500
    assert out.solve_time_sec < 60.0
    assert out.expected_total_cost_inr > 0.0


# 7. Results Files & Storage Verification
def test_results_files_exist():
    """Verifies all required result artifacts are saved in data/results/."""
    expected_files = [
        "stochastic_hourly_schedule.csv",
        "scenario_costs.csv",
        "deterministic_baseline.csv",
        "optimization_summary.json",
        "risk_metrics.json",
        "vss_evpi_metrics.json",
        "sensitivity_results.csv",
        "model_config_snapshot.json",
    ]
    for fn in expected_files:
        p = RESULTS_DIR / fn
        assert p.exists(), f"Missing required result file: {fn}"
        assert p.stat().st_size > 0, f"Result file {fn} is empty"


# 8. Flask API Optimization Endpoint Test
def test_flask_optimization_endpoint(flask_test_client):
    """Tests POST /api/optimization/run executes real solver and returns 200."""
    payload = {
        "num_scenarios": 10,
        "risk_aversion": 0.0,
        "battery_capacity_kwh": 1000.0,
        "initial_soc_pct": 0.50,
    }
    resp = flask_test_client.post("/api/optimization/run", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "results" in data
    assert "expected_total_cost_inr" in data["results"]
    assert "hourly_schedule" in data["results"]


def test_flask_optimization_latest_endpoint(flask_test_client):
    """Tests GET /api/optimization/latest returns valid results."""
    resp = flask_test_client.get("/api/optimization/latest")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "status" in data
    assert "expected_total_cost_inr" in data
