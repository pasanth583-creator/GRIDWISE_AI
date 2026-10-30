"""
GRIDWISE AI - Optimization Service Layer
Bridges Flask HTTP/API layer with Stochastic Optimization Engine and SQLite persistence.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
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


class OptimizationService:
    """Service providing end-to-end optimization management and persistence."""

    @classmethod
    def run_optimization(
        cls,
        num_scenarios: int = 500,
        risk_aversion_lambda: float = 0.0,
        battery_capacity_kwh: float = 1000.0,
        max_charge_kw: float = 400.0,
        max_discharge_kw: float = 400.0,
        initial_soc_pct: float = 0.50,
        run_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes real two-stage stochastic optimization and logs to SQLite and data/results/.
        """
        logger.info(
            f"OptimizationService.run_optimization: N={num_scenarios}, lambda={risk_aversion_lambda}, "
            f"Battery={battery_capacity_kwh}kWh"
        )

        battery = BatteryParameters(
            capacity_kwh=battery_capacity_kwh,
            max_charge_kw=max_charge_kw,
            max_discharge_kw=max_discharge_kw,
            initial_soc_pct=initial_soc_pct,
            charging_efficiency=0.92,
            discharging_efficiency=0.92,
        )
        grid = GridParameters(
            max_day_ahead_import_kw=1000.0,
            max_real_time_import_kw=1000.0,
            max_total_import_kw=1000.0,
            max_export_kw=500.0,
        )

        optimizer = StochasticOptimizer(battery_params=battery, grid_params=grid)

        # 1. Load validated scenarios
        scenarios_df, meta = ScenarioLoader.load_and_validate(max_scenarios=num_scenarios)

        # 2. Solve Stochastic Model (RP)
        stochastic_out = optimizer.solve_stochastic_model(
            scenarios_df=scenarios_df,
            risk_weight_lambda=risk_aversion_lambda,
        )

        # 3. Solve Deterministic Baseline & Compute VSS
        x_det, eev_cost, ev_obj, diag = optimizer.solve_deterministic_baseline(scenarios_df)
        vss_val = max(0.0, eev_cost - stochastic_out.expected_total_cost_inr)
        vss_pct = (vss_val / eev_cost * 100.0) if eev_cost > 0 else 0.0

        # 4. Solve Wait-and-See (WS) & Compute EVPI
        ws_cost, _ = optimizer.solve_wait_and_see(scenarios_df)
        evpi_val = max(0.0, stochastic_out.expected_total_cost_inr - ws_cost)

        # 5. Save all results
        weather_map = scenarios_df.groupby("scenario_id")["weather_condition"].first().to_dict()
        weather_conds = [weather_map.get(sid, "Unknown") for sid in stochastic_out.scenario_ids]

        saved_paths = optimizer.save_all_results(
            stochastic_out=stochastic_out,
            x_det=x_det,
            eev_cost=eev_cost,
            evpi_val=evpi_val,
            ws_cost=ws_cost,
            weather_conditions=weather_conds,
        )

        # 6. Persist run to SQLite database
        run_uuid = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        if not run_name:
            run_name = f"Stochastic 2-Stage (N={num_scenarios}, λ={risk_aversion_lambda})"

        run_id = None
        try:
            total_da_kwh = float(np.sum(stochastic_out.day_ahead_schedule_kw))
            total_rt_kwh = float(np.sum(stochastic_out.expected_real_time_import_kw))
            total_cycled_kwh = float(np.sum(stochastic_out.expected_battery_discharge_kw))
            total_exp_kwh = float(np.sum(stochastic_out.expected_export_kw))

            run_id = execute_db(
                """
                INSERT INTO optimization_runs (
                    run_uuid, run_name, run_date, formulation_type, status,
                    num_scenarios, solver_name, total_procurement_cost, baseline_cost,
                    cost_savings_pct, total_solar_used_kwh, total_grid_imported_kwh,
                    total_grid_exported_kwh, total_battery_cycled_kwh, solver_runtime_sec, notes
                ) VALUES (?, ?, DATE('now'), ?, 'COMPLETED', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_uuid,
                    run_name,
                    "Two-Stage Stochastic (Mean-CVaR)" if risk_aversion_lambda > 0 else "Two-Stage Stochastic",
                    len(stochastic_out.scenario_ids),
                    "SciPy HiGHS (Interior Point)",
                    round(stochastic_out.expected_total_cost_inr, 2),
                    round(eev_cost, 2),
                    round(vss_pct, 2),
                    3285.0,  # Expected daily solar
                    round(total_da_kwh + total_rt_kwh, 1),
                    round(total_exp_kwh, 1),
                    round(total_cycled_kwh, 1),
                    round(stochastic_out.solve_time_sec, 3),
                    f"VSS: INR {vss_val:,.2f}, EVPI: INR {evpi_val:,.2f}, CVaR_95: INR {stochastic_out.cvar_95_cost_inr:,.2f}",
                ),
            )

            # Persist hourly schedule to optimization_schedule
            for t in range(24):
                execute_db(
                    """
                    INSERT INTO optimization_schedule (
                        run_id, hour, grid_import_kw, grid_export_kw, solar_used_kw,
                        solar_curtailed_kw, bess_charge_kw, bess_discharge_kw,
                        bess_soc_kwh, bess_soc_pct, campus_load_kw, hourly_cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        t,
                        round(float(stochastic_out.day_ahead_schedule_kw[t] + stochastic_out.expected_real_time_import_kw[t]), 2),
                        round(float(stochastic_out.expected_export_kw[t]), 2),
                        0.0,
                        0.0,
                        round(float(stochastic_out.expected_battery_charge_kw[t]), 2),
                        round(float(stochastic_out.expected_battery_discharge_kw[t]), 2),
                        round(float(stochastic_out.expected_battery_soc_kwh[t]), 2),
                        round(float(stochastic_out.expected_battery_soc_pct[t]), 2),
                        0.0,
                        round(float(stochastic_out.day_ahead_schedule_kw[t] * 7.5), 2),
                    ),
                )
        except Exception as db_err:
            logger.warning(f"Failed to record run into SQLite (non-fatal): {db_err}")

        summary = stochastic_out.get_summary_dict()
        summary["run_uuid"] = run_uuid
        summary["vss_inr"] = round(vss_val, 2)
        summary["vss_savings_pct"] = round(vss_pct, 2)
        summary["evpi_inr"] = round(evpi_val, 2)
        summary["deterministic_baseline_eev_inr"] = round(eev_cost, 2)
        summary["hourly_schedule"] = stochastic_out.get_hourly_dataframe().to_dict(orient="records")

        return summary

    @classmethod
    def get_latest_results(cls) -> Dict[str, Any]:
        """Loads latest saved results or returns default summary."""
        sum_path = RESULTS_DIR / "optimization_summary.json"
        sched_path = RESULTS_DIR / "stochastic_hourly_schedule.csv"

        if sum_path.exists():
            with open(sum_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if sched_path.exists():
                df = pd.read_csv(sched_path)
                data["hourly_schedule"] = df.to_dict(orient="records")
            return data

        # If not yet executed, run optimization now to populate real results
        return cls.run_optimization(num_scenarios=500, risk_aversion_lambda=0.0)

    @classmethod
    def get_sensitivity_results(cls) -> List[Dict[str, Any]]:
        """Returns sensitivity outcomes as list of dicts."""
        sens_path = RESULTS_DIR / "sensitivity_results.csv"
        if sens_path.exists():
            df = pd.read_csv(sens_path)
            return df.to_dict(orient="records")
        return []

