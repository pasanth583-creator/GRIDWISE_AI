"""
GRIDWISE AI - What-If Simulation Laboratory Service
Phase 9 Multi-Objective Optimization & Intelligent Decision Support

Runs isolated parametric microgrid experiments (asset sizing, demand scaling,
tariff shocks, weather variability, and risk postures) without altering production configs.
Compares experimental outcomes directly against baseline optimization runs.
"""

from typing import Dict, Any, Optional, List
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


class WhatIfSimulationService:
    """Provides isolated parametric experiment execution and comparative analytics."""

    @classmethod
    def run_experiment(
        cls,
        experiment_name: str,
        solar_capacity_kw: float = 800.0,
        battery_capacity_kwh: float = 1000.0,
        battery_power_kw: float = 400.0,
        demand_scale: float = 1.0,
        price_scale: float = 1.0,
        solar_scale: float = 1.0,
        risk_aversion_lambda: float = 0.0,
        num_scenarios: int = 50,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Executes an isolated simulation experiment with user-modified parameters.
        Does not mutate the production microgrid_config database table.
        """
        exp_uuid = f"EXP-{uuid.uuid4().hex[:8].upper()}"

        # 1. Load Scenarios
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

        # 2. Apply Parametric Scaling to Scenarios in isolated copy
        exp_df = scenarios_df.copy()
        exp_df["demand_kwh"] = np.maximum(50.0, exp_df["demand_kwh"] * float(demand_scale))
        exp_df["solar_kwh"] = np.clip(
            exp_df["solar_kwh"] * float(solar_scale) * (solar_capacity_kw / 800.0),
            0.0,
            solar_capacity_kw,
        )
        exp_df["day_ahead_price_inr_kwh"] = np.maximum(0.5, exp_df["day_ahead_price_inr_kwh"] * float(price_scale))
        exp_df["real_time_price_inr_kwh"] = np.maximum(0.5, exp_df["real_time_price_inr_kwh"] * float(price_scale))

        # 3. Configure Experimental Microgrid Asset Limits
        battery = BatteryParameters(
            capacity_kwh=float(battery_capacity_kwh),
            max_charge_kw=float(battery_power_kw),
            max_discharge_kw=float(battery_power_kw),
            initial_soc_pct=0.50,
            charging_efficiency=0.92,
            discharging_efficiency=0.92,
            degradation_cost_inr_kwh=0.35,
        )

        grid = GridParameters(
            max_day_ahead_import_kw=1000.0,
            max_real_time_import_kw=1000.0,
            max_total_import_kw=1000.0,
            max_export_kw=500.0,
        )

        optimizer = StochasticOptimizer(battery_params=battery, grid_params=grid)

        # 4. Solve Experimental Stochastic LP
        stochastic_out = optimizer.solve_stochastic_model(
            scenarios_df=exp_df,
            risk_weight_lambda=float(risk_aversion_lambda),
        )

        # 5. Solve EEV Baseline on modified scenarios
        x_det, eev_cost, ev_obj, _ = optimizer.solve_deterministic_baseline(exp_df)
        vss_val = max(0.0, eev_cost - stochastic_out.expected_total_cost_inr)

        # 6. Retrieve Production Baseline (e.g. from adaptive_optimization_runs)
        baseline_cost = 48021.86  # Standard Phase 8 baseline cost
        baseline_cvar = 58046.35
        baseline_uuid = "PHASE8-BASELINE"

        try:
            last_run = query_db(
                "SELECT run_uuid, expected_cost_inr, cvar_95_inr FROM adaptive_optimization_runs ORDER BY id DESC LIMIT 1",
                one=True,
            )
            if last_run:
                baseline_cost = float(last_run["expected_cost_inr"])
                baseline_cvar = float(last_run["cvar_95_inr"])
                baseline_uuid = last_run["run_uuid"]
        except Exception:
            pass

        cost_delta = round(stochastic_out.expected_total_cost_inr - baseline_cost, 2)
        cvar_delta = round(stochastic_out.cvar_95_cost_inr - baseline_cvar, 2)
        pct_cost_change = round(cost_delta / baseline_cost * 100.0, 2) if baseline_cost > 0 else 0.0

        modified_params = {
            "solar_capacity_kw": solar_capacity_kw,
            "battery_capacity_kwh": battery_capacity_kwh,
            "battery_power_kw": battery_power_kw,
            "demand_scale": demand_scale,
            "price_scale": price_scale,
            "solar_scale": solar_scale,
            "risk_aversion_lambda": risk_aversion_lambda,
            "num_scenarios": num_scenarios,
        }

        exp_result = {
            "experiment_uuid": exp_uuid,
            "experiment_name": experiment_name or f"What-If Experiment {exp_uuid[:6]}",
            "baseline_run_uuid": baseline_uuid,
            "modified_params": modified_params,
            "results": {
                "expected_cost_inr": round(stochastic_out.expected_total_cost_inr, 2),
                "baseline_cost_inr": round(baseline_cost, 2),
                "cost_delta_inr": cost_delta,
                "pct_cost_change": pct_cost_change,
                "cvar_95_inr": round(stochastic_out.cvar_95_cost_inr, 2),
                "baseline_cvar_inr": round(baseline_cvar, 2),
                "cvar_delta_inr": cvar_delta,
                "vss_inr": round(vss_val, 2),
                "solver_status": "OPTIMAL" if stochastic_out.success else "FAILED",
                "solve_time_sec": round(stochastic_out.solve_time_sec, 3),
            },
            "schedule": {
                "day_ahead_schedule_kw": [round(float(v), 2) for v in stochastic_out.day_ahead_schedule_kw],
                "expected_soc_kwh": [round(float(v), 2) for v in stochastic_out.expected_battery_soc_kwh],
            },
            "notes": notes,
        }

        # Persist to SQLite table what_if_experiments
        try:
            execute_db(
                """
                INSERT INTO what_if_experiments (
                    experiment_uuid, experiment_name, baseline_run_uuid,
                    modified_params_json, expected_cost_inr, baseline_cost_inr,
                    cost_delta_inr, cvar_95_inr, baseline_cvar_inr,
                    cvar_delta_inr, vss_inr, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exp_uuid,
                    exp_result["experiment_name"],
                    baseline_uuid,
                    json.dumps(modified_params),
                    exp_result["results"]["expected_cost_inr"],
                    exp_result["results"]["baseline_cost_inr"],
                    cost_delta,
                    exp_result["results"]["cvar_95_inr"],
                    exp_result["results"]["baseline_cvar_inr"],
                    cvar_delta,
                    exp_result["results"]["vss_inr"],
                    notes,
                ),
            )
        except Exception as e:
            logger.warning(f"Could not persist what_if_experiment: {e}")

        return exp_result

    @classmethod
    def get_experiment_history(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """Queries historical what-if experiments from SQLite."""
        try:
            rows = query_db(
                """
                SELECT experiment_uuid, experiment_name, baseline_run_uuid,
                       modified_params_json, expected_cost_inr, baseline_cost_inr,
                       cost_delta_inr, cvar_95_inr, baseline_cvar_inr,
                       cvar_delta_inr, vss_inr, notes, created_at
                FROM what_if_experiments
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["modified_params"] = json.loads(d["modified_params_json"])
                except Exception:
                    d["modified_params"] = {}
                results.append(d)
            return results
        except Exception as e:
            logger.error(f"Error querying what-if history: {e}")
            return []

