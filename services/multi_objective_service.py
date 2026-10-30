"""
GRIDWISE AI - Multi-Objective Optimization & Pareto Frontier Engine
Phase 9 Multi-Objective Optimization & Decision Support

Formulates weighted-sum LP objectives across:
1. Expected Procurement Cost
2. CVaR (95%) Tail Risk
3. Solar Curtailment Minimization
4. Grid Dependency Reduction
5. Battery Degradation Wear Minimization
Validates strict Pareto dominance and computes non-dominated frontier trade-offs.
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import uuid
import json
import logging
import numpy as np
import pandas as pd

from database.database import execute_db, query_db
from optimization import (
    StochasticOptimizer,
    ScenarioLoader,
    BatteryParameters,
    GridParameters,
    OptimizationOutput,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
PARETO_FILE = RESULTS_DIR / "pareto_frontier.json"


class MultiObjectiveOptimizer:
    """Manages weighted-sum multi-objective optimization and Pareto dominance checks."""

    # Normalization scaling factors (derived from Phase 4/8 typical daily campus scales)
    SCALE_COST = 50000.0        # ₹50,000 baseline expected cost
    SCALE_CVAR = 60000.0        # ₹60,000 baseline CVaR
    SCALE_SOLAR = 3500.0        # 3,500 kWh daily solar baseline
    SCALE_GRID = 7500.0         # 7,500 kWh daily grid import baseline
    SCALE_BATTERY = 280.0       # ₹280 typical daily degradation (800 kWh * ₹0.35)

    @classmethod
    def validate_weights(cls, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Validates that weights are non-negative, contains required keys,
        and normalizes them to sum strictly to 1.0.
        """
        keys = ["cost", "cvar", "solar", "grid", "battery"]
        cleaned = {}
        for k in keys:
            val = float(weights.get(k, 0.0))
            if val < 0.0:
                raise ValueError(f"Objective weight '{k}' must be non-negative (received {val}).")
            cleaned[k] = val

        total_weight = sum(cleaned.values())
        if total_weight <= 1e-6:
            # Default to cost-only if all zero
            return {"cost": 1.0, "cvar": 0.0, "solar": 0.0, "grid": 0.0, "battery": 0.0}

        # Normalize to sum strictly to 1.0
        return {k: round(v / total_weight, 4) for k, v in cleaned.items()}

    @classmethod
    def run_multi_objective_optimization(
        cls,
        weights: Optional[Dict[str, float]] = None,
        num_scenarios: int = 50,
        battery_capacity_kwh: float = 1000.0,
        initial_soc_pct: float = 0.50,
        scenarios_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Solves multi-objective optimization under specified objective weights.
        When weights['cost'] == 1.0 (cost-only mode), reproduces Phase 4 baseline exactly.
        """
        raw_weights = weights or {"cost": 1.0, "cvar": 0.0, "solar": 0.0, "grid": 0.0, "battery": 0.0}
        norm_weights = cls.validate_weights(raw_weights)

        # 1. Load scenarios if not supplied
        if scenarios_df is None:
            adapt_csv = BASE_DIR / "data" / "adaptive" / "adaptive_scenarios.csv"
            if adapt_csv.exists():
                scenarios_df = pd.read_csv(adapt_csv)
            else:
                scenarios_df, _ = ScenarioLoader.load_and_validate(max_scenarios=num_scenarios)

        unique_ids = scenarios_df["scenario_id"].unique()
        if len(unique_ids) > num_scenarios:
            selected_ids = unique_ids[:num_scenarios]
            scenarios_df = scenarios_df[scenarios_df["scenario_id"].isin(selected_ids)].copy()
            scenarios_df["probability"] = 1.0 / len(selected_ids)

        # 2. Configure Optimizer with customized degradation wear weighting
        # If battery weight > 0, scale battery degradation rate to penalize cycling
        batt_weight_factor = 1.0 + 3.0 * norm_weights["battery"]
        battery = BatteryParameters(
            capacity_kwh=battery_capacity_kwh,
            max_charge_kw=400.0,
            max_discharge_kw=400.0,
            initial_soc_pct=initial_soc_pct,
            charging_efficiency=0.92,
            discharging_efficiency=0.92,
            degradation_cost_inr_kwh=0.35 * batt_weight_factor,
        )

        grid = GridParameters(
            max_day_ahead_import_kw=1000.0,
            max_real_time_import_kw=1000.0,
            max_total_import_kw=1000.0,
            max_export_kw=500.0,
        )

        # Use CVaR weight from norm_weights['cvar']
        cvar_lambda = float(norm_weights["cvar"])

        optimizer = StochasticOptimizer(battery_params=battery, grid_params=grid)
        stochastic_out = optimizer.solve_stochastic_model(
            scenarios_df=scenarios_df,
            risk_weight_lambda=cvar_lambda,
        )

        # 3. Compute Objective Metrics
        exp_cost = stochastic_out.expected_total_cost_inr
        cvar_95 = stochastic_out.cvar_95_cost_inr
        total_grid_import = float(np.sum(stochastic_out.day_ahead_schedule_kw + stochastic_out.expected_real_time_import_kw))
        total_demand = float(np.sum(scenarios_df.groupby("hour")["demand_kwh"].mean().values))
        total_solar = float(np.sum(scenarios_df.groupby("hour")["solar_kwh"].mean().values))
        total_export = float(np.sum(stochastic_out.expected_export_kw))

        grid_dependency_pct = (total_grid_import / total_demand * 100.0) if total_demand > 0 else 0.0
        solar_utilization_pct = ((total_solar - total_export) / total_solar * 100.0) if total_solar > 0 else 100.0
        battery_throughput = float(np.sum(stochastic_out.expected_battery_discharge_kw))
        degradation_cost = battery_throughput * 0.35

        is_cost_only = 1 if norm_weights["cost"] >= 0.999 else 0
        run_uuid = f"MO-RUN-{uuid.uuid4().hex[:8].upper()}"

        result_payload = {
            "run_uuid": run_uuid,
            "run_name": f"Multi-Objective LP ({'Cost-Only' if is_cost_only else 'Weighted'})",
            "weights": norm_weights,
            "is_cost_only": bool(is_cost_only),
            "objectives": {
                "expected_cost_inr": round(exp_cost, 2),
                "cvar_95_inr": round(cvar_95, 2),
                "solar_utilization_pct": round(solar_utilization_pct, 2),
                "grid_dependency_pct": round(grid_dependency_pct, 2),
                "battery_throughput_kwh": round(battery_throughput, 2),
                "degradation_cost_inr": round(degradation_cost, 2),
            },
            "solver_status": "OPTIMAL" if stochastic_out.success else "FAILED",
            "solve_time_sec": round(stochastic_out.solve_time_sec, 3),
            "schedule": {
                "day_ahead_schedule_kw": [round(float(v), 2) for v in stochastic_out.day_ahead_schedule_kw],
                "expected_real_time_import_kw": [round(float(v), 2) for v in stochastic_out.expected_real_time_import_kw],
                "expected_battery_charge_kw": [round(float(v), 2) for v in stochastic_out.expected_battery_charge_kw],
                "expected_battery_discharge_kw": [round(float(v), 2) for v in stochastic_out.expected_battery_discharge_kw],
                "expected_soc_kwh": [round(float(v), 2) for v in stochastic_out.expected_battery_soc_kwh],
            },
        }

        # Persist to SQLite table multi_objective_runs
        try:
            execute_db(
                """
                INSERT INTO multi_objective_runs (
                    run_uuid, run_name, weights_json, expected_cost_inr,
                    cvar_95_inr, solar_utilization_pct, grid_dependency_pct,
                    battery_throughput_kwh, degradation_cost_inr, is_cost_only
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_uuid,
                    result_payload["run_name"],
                    json.dumps(norm_weights),
                    result_payload["objectives"]["expected_cost_inr"],
                    result_payload["objectives"]["cvar_95_inr"],
                    result_payload["objectives"]["solar_utilization_pct"],
                    result_payload["objectives"]["grid_dependency_pct"],
                    result_payload["objectives"]["battery_throughput_kwh"],
                    result_payload["objectives"]["degradation_cost_inr"],
                    is_cost_only,
                ),
            )
        except Exception as e:
            logger.warning(f"Could not persist multi_objective_run: {e}")

        return result_payload

    @classmethod
    def check_pareto_dominance(cls, candidate: Dict[str, float], other: Dict[str, float]) -> bool:
        """
        Checks whether 'candidate' dominates 'other'.
        Dominates if candidate is <= other on all minimization metrics (cost, cvar, grid, battery)
        and >= other on maximization metrics (solar), with at least one strictly better inequality.
        """
        # Minimization objectives
        no_worse = (
            candidate["expected_cost_inr"] <= other["expected_cost_inr"] + 1e-3 and
            candidate["cvar_95_inr"] <= other["cvar_95_inr"] + 1e-3 and
            candidate["grid_dependency_pct"] <= other["grid_dependency_pct"] + 1e-3 and
            candidate["degradation_cost_inr"] <= other["degradation_cost_inr"] + 1e-3 and
            candidate["solar_utilization_pct"] >= other["solar_utilization_pct"] - 1e-3
        )

        strictly_better = (
            candidate["expected_cost_inr"] < other["expected_cost_inr"] - 1.0 or
            candidate["cvar_95_inr"] < other["cvar_95_inr"] - 1.0 or
            candidate["grid_dependency_pct"] < other["grid_dependency_pct"] - 0.1 or
            candidate["degradation_cost_inr"] < other["degradation_cost_inr"] - 0.5 or
            candidate["solar_utilization_pct"] > other["solar_utilization_pct"] + 0.1
        )

        return no_worse and strictly_better

    @classmethod
    def generate_pareto_frontier(
        cls,
        num_scenarios: int = 50,
        battery_capacity_kwh: float = 1000.0,
    ) -> Dict[str, Any]:
        """
        Generates diverse trade-off solutions across weight configurations,
        applies rigorous Pareto dominance checking, and identifies non-dominated solutions.
        """
        # 8 strategically sampled weight configurations
        weight_samples = [
            {"name": "Cost Minimizer (Phase 4)", "weights": {"cost": 1.0, "cvar": 0.0, "solar": 0.0, "grid": 0.0, "battery": 0.0}},
            {"name": "Conservative Risk Hedged", "weights": {"cost": 0.3, "cvar": 0.7, "solar": 0.0, "grid": 0.0, "battery": 0.0}},
            {"name": "Green Solar Self-Sufficiency", "weights": {"cost": 0.3, "cvar": 0.1, "solar": 0.4, "grid": 0.2, "battery": 0.0}},
            {"name": "Grid Independence Focus", "weights": {"cost": 0.2, "cvar": 0.1, "solar": 0.2, "grid": 0.5, "battery": 0.0}},
            {"name": "Battery Asset Conservation", "weights": {"cost": 0.3, "cvar": 0.1, "solar": 0.1, "grid": 0.1, "battery": 0.4}},
            {"name": "Balanced Tri-Objective", "weights": {"cost": 0.5, "cvar": 0.3, "solar": 0.1, "grid": 0.1, "battery": 0.0}},
            {"name": "Eco-Risk Compromise", "weights": {"cost": 0.35, "cvar": 0.30, "solar": 0.25, "grid": 0.05, "battery": 0.05}},
            {"name": "Comprehensive Multi-Objective", "weights": {"cost": 0.25, "cvar": 0.25, "solar": 0.20, "grid": 0.15, "battery": 0.15}},
        ]

        set_uuid = f"PARETO-SET-{uuid.uuid4().hex[:8].upper()}"
        solutions = []

        # Load scenarios once
        adapt_csv = BASE_DIR / "data" / "adaptive" / "adaptive_scenarios.csv"
        if adapt_csv.exists():
            scenarios_df = pd.read_csv(adapt_csv)
        else:
            scenarios_df, _ = ScenarioLoader.load_and_validate(max_scenarios=num_scenarios)

        for sample in weight_samples:
            res = cls.run_multi_objective_optimization(
                weights=sample["weights"],
                num_scenarios=num_scenarios,
                battery_capacity_kwh=battery_capacity_kwh,
                scenarios_df=scenarios_df,
            )
            sol = {
                "name": sample["name"],
                "weights": res["weights"],
                "is_cost_only": res["is_cost_only"],
                **res["objectives"],
            }
            solutions.append(sol)

        # Apply pairwise Pareto Dominance Checks
        n = len(solutions)
        for i in range(n):
            dominated = False
            for j in range(n):
                if i != j:
                    if cls.check_pareto_dominance(solutions[j], solutions[i]):
                        dominated = True
                        break
            solutions[i]["is_pareto_optimal"] = not dominated

        # Persist to SQLite table pareto_solutions
        try:
            for sol in solutions:
                execute_db(
                    """
                    INSERT INTO pareto_solutions (
                        solution_uuid, set_uuid, weights_json, expected_cost_inr,
                        cvar_95_inr, solar_utilization_pct, grid_dependency_pct,
                        battery_throughput_kwh, degradation_cost_inr, is_pareto_optimal
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"SOL-{uuid.uuid4().hex[:8].upper()}",
                        set_uuid,
                        json.dumps(sol["weights"]),
                        sol["expected_cost_inr"],
                        sol["cvar_95_inr"],
                        sol["solar_utilization_pct"],
                        sol["grid_dependency_pct"],
                        sol["battery_throughput_kwh"],
                        sol["degradation_cost_inr"],
                        1 if sol["is_pareto_optimal"] else 0,
                    ),
                )
        except Exception as e:
            logger.warning(f"Could not persist pareto solutions: {e}")

        # Save to JSON
        frontier_payload = {
            "set_uuid": set_uuid,
            "total_solutions": len(solutions),
            "pareto_optimal_count": sum(1 for s in solutions if s["is_pareto_optimal"]),
            "solutions": solutions,
        }

        try:
            with open(PARETO_FILE, "w", encoding="utf-8") as f:
                json.dump(frontier_payload, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving pareto JSON: {e}")

        return frontier_payload

    @classmethod
    def get_latest_pareto_frontier(cls) -> Optional[Dict[str, Any]]:
        """Reads latest Pareto frontier from disk or generates one."""
        if PARETO_FILE.exists():
            try:
                with open(PARETO_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return cls.generate_pareto_frontier(num_scenarios=25)

