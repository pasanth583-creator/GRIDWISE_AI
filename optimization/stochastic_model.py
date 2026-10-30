"""
GRIDWISE AI - Stochastic Optimization Engine
Coordinates Two-Stage Stochastic Linear Programming, Deterministic Baselines, VSS, EVPI, and Sensitivity Analysis.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json
import time
import logging
import numpy as np
import pandas as pd

from optimization.scenario_loader import ScenarioLoader, ScenarioValidationError
from optimization.battery_model import BatteryParameters, GridParameters
from optimization.objective import ObjectiveBuilder
from optimization.constraints import ConstraintBuilder
from optimization.solver import LinearSolver, SolverResult, OptimizationSolverError
from optimization.optimization_results import OptimizationOutput, ResultsParser

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class StochasticOptimizer:
    """End-to-end two-stage stochastic optimization engine for campus microgrid."""

    def __init__(
        self,
        battery_params: Optional[BatteryParameters] = None,
        grid_params: Optional[GridParameters] = None,
    ):
        self.battery_params = battery_params or BatteryParameters()
        self.grid_params = grid_params or GridParameters()

    def solve_stochastic_model(
        self,
        scenarios_df: Optional[pd.DataFrame] = None,
        max_scenarios: Optional[int] = None,
        risk_weight_lambda: float = 0.0,
        confidence_alpha: float = 0.95,
        time_limit_sec: float = 60.0,
    ) -> OptimizationOutput:
        """
        Solves the Two-Stage Stochastic Linear Program with optional CVaR risk aversion.
        """
        if scenarios_df is None:
            scenarios_df, _ = ScenarioLoader.load_and_validate(max_scenarios=max_scenarios)
        elif max_scenarios is not None and len(scenarios_df["scenario_id"].unique()) > max_scenarios:
            selected = scenarios_df["scenario_id"].unique()[:max_scenarios]
            scenarios_df = scenarios_df[scenarios_df["scenario_id"].isin(selected)].copy()
            # Normalize probabilities
            probs = scenarios_df.groupby("scenario_id")["probability"].first()
            norm = float(probs.sum())
            scenarios_df["probability"] = scenarios_df["scenario_id"].map((probs / norm).to_dict())

        scenario_ids = list(scenarios_df["scenario_id"].unique())
        N = len(scenario_ids)
        T = 24

        probs = scenarios_df.groupby("scenario_id")["probability"].first().loc[scenario_ids].values

        # Reshape demand, solar, and prices into (N, 24)
        demand_mat = scenarios_df.pivot(index="scenario_id", columns="hour", values="demand_kwh").loc[scenario_ids].values
        solar_mat = scenarios_df.pivot(index="scenario_id", columns="hour", values="solar_kwh").loc[scenario_ids].values

        if "day_ahead_price_inr_kwh" in scenarios_df.columns:
            da_prices = scenarios_df.groupby("hour")["day_ahead_price_inr_kwh"].first().sort_index().values
        else:
            da_prices = np.array([4.2]*6 + [7.5]*8 + [11.8]*6 + [7.5]*2 + [4.2]*2)

        if "real_time_price_inr_kwh" in scenarios_df.columns:
            rt_mat = scenarios_df.pivot(index="scenario_id", columns="hour", values="real_time_price_inr_kwh").loc[scenario_ids].values
        else:
            rt_mat = np.tile(da_prices * 1.05, (N, 1))

        # 1. Build Objective
        c, idx_map = ObjectiveBuilder.build_objective_vector(
            num_scenarios=N,
            probabilities=probs,
            da_prices_24h=da_prices,
            rt_prices_matrix=rt_mat,
            battery_params=self.battery_params,
            grid_params=self.grid_params,
            risk_weight_lambda=risk_weight_lambda,
            confidence_alpha=confidence_alpha,
            horizon_hours=T,
        )

        # 2. Build Constraints
        A_eq, b_eq, A_ub, b_ub, bounds = ConstraintBuilder.build_constraints(
            num_scenarios=N,
            demand_matrix=demand_mat,
            solar_matrix=solar_mat,
            da_prices_24h=da_prices,
            rt_prices_matrix=rt_mat,
            battery_params=self.battery_params,
            grid_params=self.grid_params,
            idx_map=idx_map,
            risk_weight_lambda=risk_weight_lambda,
        )

        # 3. Solve via HiGHS
        solver_res = LinearSolver.solve_lp(
            c=c,
            A_eq=A_eq,
            b_eq=b_eq,
            A_ub=A_ub,
            b_ub=b_ub,
            bounds=bounds,
            time_limit_sec=time_limit_sec,
        )

        # 4. Parse Solution
        output = ResultsParser.parse_solution(
            solver_res=solver_res,
            idx_map=idx_map,
            scenario_ids=scenario_ids,
            probabilities=probs,
            da_prices_24h=da_prices,
            rt_prices_matrix=rt_mat,
            battery_params=self.battery_params,
            grid_params=self.grid_params,
            risk_weight_lambda=risk_weight_lambda,
        )

        return output

    def solve_deterministic_baseline(
        self,
        scenarios_df: pd.DataFrame,
        time_limit_sec: float = 60.0,
    ) -> Tuple[np.ndarray, float, float, Dict[str, Any]]:
        """
        Calculates the true Expected Value of the Expected Value solution (EEV) and Value of Stochastic Solution (VSS).

        Procedure:
        1. Formulate deterministic model using expected demand E[D(t)] and expected solar E[PV(t)].
        2. Solve to find deterministic day-ahead contract schedule x_det[t].
        3. Fix x_da = x_det[t] and evaluate its recourse cost across all N uncertainty scenarios (EEV).
        4. VSS = EEV - RP (where RP is the stochastic recourse problem optimal expected cost).

        Returns
        -------
        Tuple[x_det, eev_expected_cost, deterministic_ev_cost, diagnostics]
        """
        logger.info("Computing Deterministic Expected-Value baseline...")
        scenario_ids = list(scenarios_df["scenario_id"].unique())
        N = len(scenario_ids)
        T = 24

        probs = scenarios_df.groupby("scenario_id")["probability"].first().loc[scenario_ids].values
        demand_mat = scenarios_df.pivot(index="scenario_id", columns="hour", values="demand_kwh").loc[scenario_ids].values
        solar_mat = scenarios_df.pivot(index="scenario_id", columns="hour", values="solar_kwh").loc[scenario_ids].values

        if "day_ahead_price_inr_kwh" in scenarios_df.columns:
            da_prices = scenarios_df.groupby("hour")["day_ahead_price_inr_kwh"].first().sort_index().values
        else:
            da_prices = np.array([4.2]*6 + [7.5]*8 + [11.8]*6 + [7.5]*2 + [4.2]*2)

        if "real_time_price_inr_kwh" in scenarios_df.columns:
            rt_mat = scenarios_df.pivot(index="scenario_id", columns="hour", values="real_time_price_inr_kwh").loc[scenario_ids].values
        else:
            rt_mat = np.tile(da_prices * 1.05, (N, 1))

        # Expected single scenario: (1, 24)
        exp_demand = np.sum(demand_mat * probs[:, np.newaxis], axis=0, keepdims=True)
        exp_solar = np.sum(solar_mat * probs[:, np.newaxis], axis=0, keepdims=True)
        exp_rt = np.sum(rt_mat * probs[:, np.newaxis], axis=0, keepdims=True)
        single_prob = np.array([1.0])

        # Step 1: Solve Expected Value (EV) model for N=1
        c_ev, idx_map_ev = ObjectiveBuilder.build_objective_vector(
            num_scenarios=1,
            probabilities=single_prob,
            da_prices_24h=da_prices,
            rt_prices_matrix=exp_rt,
            battery_params=self.battery_params,
            grid_params=self.grid_params,
            risk_weight_lambda=0.0,
            horizon_hours=T,
        )
        A_eq_ev, b_eq_ev, A_ub_ev, b_ub_ev, bounds_ev = ConstraintBuilder.build_constraints(
            num_scenarios=1,
            demand_matrix=exp_demand,
            solar_matrix=exp_solar,
            da_prices_24h=da_prices,
            rt_prices_matrix=exp_rt,
            battery_params=self.battery_params,
            grid_params=self.grid_params,
            idx_map=idx_map_ev,
            risk_weight_lambda=0.0,
        )
        ev_solver_res = LinearSolver.solve_lp(
            c=c_ev,
            A_eq=A_eq_ev,
            b_eq=b_eq_ev,
            A_ub=A_ub_ev,
            b_ub=b_ub_ev,
            bounds=bounds_ev,
            time_limit_sec=time_limit_sec,
        )
        x_det = ev_solver_res.solution_vector[idx_map_ev["x"]]
        ev_objective_val = ev_solver_res.objective_value

        # Step 2: Fix x_da = x_det across ALL N scenarios to find EEV
        logger.info(f"Evaluating deterministic policy x_det across {N} scenarios (EEV)...")
        c_eev, idx_map_eev = ObjectiveBuilder.build_objective_vector(
            num_scenarios=N,
            probabilities=probs,
            da_prices_24h=da_prices,
            rt_prices_matrix=rt_mat,
            battery_params=self.battery_params,
            grid_params=self.grid_params,
            risk_weight_lambda=0.0,
            horizon_hours=T,
        )
        A_eq_eev, b_eq_eev, A_ub_eev, b_ub_eev, bounds_eev = ConstraintBuilder.build_constraints(
            num_scenarios=N,
            demand_matrix=demand_mat,
            solar_matrix=solar_mat,
            da_prices_24h=da_prices,
            rt_prices_matrix=rt_mat,
            battery_params=self.battery_params,
            grid_params=self.grid_params,
            idx_map=idx_map_eev,
            risk_weight_lambda=0.0,
            fixed_x_da=x_det,
        )
        eev_solver_res = LinearSolver.solve_lp(
            c=c_eev,
            A_eq=A_eq_eev,
            b_eq=b_eq_eev,
            A_ub=A_ub_eev,
            b_ub=b_ub_eev,
            bounds=bounds_eev,
            time_limit_sec=time_limit_sec,
        )
        eev_expected_cost = eev_solver_res.objective_value

        diag = {
            "ev_naive_objective_inr": round(float(ev_objective_val), 2),
            "eev_true_expected_cost_inr": round(float(eev_expected_cost), 2),
            "x_det_sum_kwh": round(float(np.sum(x_det)), 1),
        }
        logger.info(f"EEV Evaluation Completed: EEV={eev_expected_cost:.2f} INR, EV={ev_objective_val:.2f} INR")
        return x_det, eev_expected_cost, ev_objective_val, diag

    def solve_wait_and_see(
        self,
        scenarios_df: pd.DataFrame,
        time_limit_sec: float = 60.0,
    ) -> Tuple[float, np.ndarray]:
        """
        Computes Wait-and-See (WS) benchmark:
        Solves perfect-information optimization for each scenario independently.

        EVPI = RP - WS >= 0
        """
        logger.info("Computing Wait-and-See (WS) perfect information benchmark...")
        scenario_ids = list(scenarios_df["scenario_id"].unique())
        N = len(scenario_ids)
        T = 24

        probs = scenarios_df.groupby("scenario_id")["probability"].first().loc[scenario_ids].values
        demand_mat = scenarios_df.pivot(index="scenario_id", columns="hour", values="demand_kwh").loc[scenario_ids].values
        solar_mat = scenarios_df.pivot(index="scenario_id", columns="hour", values="solar_kwh").loc[scenario_ids].values

        if "day_ahead_price_inr_kwh" in scenarios_df.columns:
            da_prices = scenarios_df.groupby("hour")["day_ahead_price_inr_kwh"].first().sort_index().values
        else:
            da_prices = np.array([4.2]*6 + [7.5]*8 + [11.8]*6 + [7.5]*2 + [4.2]*2)

        if "real_time_price_inr_kwh" in scenarios_df.columns:
            rt_mat = scenarios_df.pivot(index="scenario_id", columns="hour", values="real_time_price_inr_kwh").loc[scenario_ids].values
        else:
            rt_mat = np.tile(da_prices * 1.05, (N, 1))

        ws_scenario_costs = np.zeros(N, dtype=float)
        single_prob = np.array([1.0])

        # Pre-build structure for N=1 once
        c_1, idx_1 = ObjectiveBuilder.build_objective_vector(
            num_scenarios=1,
            probabilities=single_prob,
            da_prices_24h=da_prices,
            rt_prices_matrix=rt_mat[0:1, :],
            battery_params=self.battery_params,
            grid_params=self.grid_params,
            risk_weight_lambda=0.0,
            horizon_hours=T,
        )

        for s in range(N):
            dem_s = demand_mat[s:s+1, :]
            sol_s = solar_mat[s:s+1, :]
            rt_s = rt_mat[s:s+1, :]

            # Re-update c for scenario specific RT price
            c_s = c_1.copy()
            c_s[idx_1["g_start"] : idx_1["g_start"] + T] = rt_s[0, :]

            A_eq, b_eq, A_ub, b_ub, bounds = ConstraintBuilder.build_constraints(
                num_scenarios=1,
                demand_matrix=dem_s,
                solar_matrix=sol_s,
                da_prices_24h=da_prices,
                rt_prices_matrix=rt_s,
                battery_params=self.battery_params,
                grid_params=self.grid_params,
                idx_map=idx_1,
                risk_weight_lambda=0.0,
            )
            res = LinearSolver.solve_lp(
                c=c_s,
                A_eq=A_eq,
                b_eq=b_eq,
                A_ub=A_ub,
                b_ub=b_ub,
                bounds=bounds,
                time_limit_sec=time_limit_sec,
            )
            ws_scenario_costs[s] = res.objective_value

        expected_ws_cost = float(np.sum(probs * ws_scenario_costs))
        logger.info(f"Wait-and-See Benchmark Completed: WS={expected_ws_cost:.2f} INR")
        return expected_ws_cost, ws_scenario_costs

    def run_sensitivity_analysis(
        self,
        base_scenarios_df: pd.DataFrame,
        sample_scenarios: int = 50,
    ) -> pd.DataFrame:
        """
        Evaluates real optimization outcomes across operational sensitivities:
        - Risk-aversion lambda (0.0 to 1.0)
        - Demand scaling (+/- 15%)
        - Solar scaling (+/- 25%)
        - Price tariff escalation (+15%, +30%)
        - Battery capacity (500, 1000, 1500 kWh)
        """
        logger.info(f"Running Sensitivity Analysis on {sample_scenarios} scenarios...")
        # Prepare subset scenarios
        selected_ids = base_scenarios_df["scenario_id"].unique()[:sample_scenarios]
        df_sub = base_scenarios_df[base_scenarios_df["scenario_id"].isin(selected_ids)].copy()
        sub_probs = df_sub.groupby("scenario_id")["probability"].first()
        norm = float(sub_probs.sum())
        df_sub["probability"] = df_sub["scenario_id"].map((sub_probs / norm).to_dict())

        results = []

        # 1. Risk-Aversion Sensitivities (lambda = 0.0, 0.25, 0.50, 0.75, 1.0)
        for lam in [0.0, 0.25, 0.50, 0.75, 1.0]:
            opt = StochasticOptimizer(self.battery_params, self.grid_params)
            t0 = time.perf_counter()
            out = opt.solve_stochastic_model(df_sub, risk_weight_lambda=lam)
            dur = time.perf_counter() - t0
            results.append({
                "sensitivity_category": "Risk Aversion (Lambda)",
                "parameter_variation": f"Lambda = {lam:.2f}",
                "expected_cost_inr": round(out.expected_total_cost_inr, 2),
                "var_95_inr": round(out.var_95_cost_inr, 2),
                "cvar_95_inr": round(out.cvar_95_cost_inr, 2),
                "day_ahead_energy_kwh": round(float(np.sum(out.day_ahead_schedule_kw)), 1),
                "solve_time_sec": round(dur, 3),
            })

        # 2. Demand Variations (Low -15%, Baseline 0%, High +15%)
        for dem_factor, label in [(0.85, "Demand -15%"), (1.15, "Demand +15%")]:
            df_dem = df_sub.copy()
            df_dem["demand_kwh"] = df_dem["demand_kwh"] * dem_factor
            opt = StochasticOptimizer(self.battery_params, self.grid_params)
            out = opt.solve_stochastic_model(df_dem, risk_weight_lambda=0.0)
            results.append({
                "sensitivity_category": "Campus Demand",
                "parameter_variation": label,
                "expected_cost_inr": round(out.expected_total_cost_inr, 2),
                "var_95_inr": round(out.var_95_cost_inr, 2),
                "cvar_95_inr": round(out.cvar_95_cost_inr, 2),
                "day_ahead_energy_kwh": round(float(np.sum(out.day_ahead_schedule_kw)), 1),
                "solve_time_sec": round(out.solve_time_sec, 3),
            })

        # 3. Solar PV Generation Variations (-25%, +25%)
        for sol_factor, label in [(0.75, "Solar -25% (Overcast)"), (1.25, "Solar +25% (Clear Sky)")]:
            df_sol = df_sub.copy()
            df_sol["solar_kwh"] = np.minimum(800.0, df_sol["solar_kwh"] * sol_factor)
            opt = StochasticOptimizer(self.battery_params, self.grid_params)
            out = opt.solve_stochastic_model(df_sol, risk_weight_lambda=0.0)
            results.append({
                "sensitivity_category": "Solar Generation",
                "parameter_variation": label,
                "expected_cost_inr": round(out.expected_total_cost_inr, 2),
                "var_95_inr": round(out.var_95_cost_inr, 2),
                "cvar_95_inr": round(out.cvar_95_cost_inr, 2),
                "day_ahead_energy_kwh": round(float(np.sum(out.day_ahead_schedule_kw)), 1),
                "solve_time_sec": round(out.solve_time_sec, 3),
            })

        # 4. Battery Capacity Variations (500 kWh, 1500 kWh)
        for b_cap, label in [(500.0, "BESS 500 kWh"), (1500.0, "BESS 1500 kWh")]:
            b_param = BatteryParameters(
                capacity_kwh=b_cap,
                max_charge_kw=b_cap * 0.4,
                max_discharge_kw=b_cap * 0.4,
            )
            opt = StochasticOptimizer(b_param, self.grid_params)
            out = opt.solve_stochastic_model(df_sub, risk_weight_lambda=0.0)
            results.append({
                "sensitivity_category": "Battery Capacity",
                "parameter_variation": label,
                "expected_cost_inr": round(out.expected_total_cost_inr, 2),
                "var_95_inr": round(out.var_95_cost_inr, 2),
                "cvar_95_inr": round(out.cvar_95_cost_inr, 2),
                "day_ahead_energy_kwh": round(float(np.sum(out.day_ahead_schedule_kw)), 1),
                "solve_time_sec": round(out.solve_time_sec, 3),
            })

        # 5. Electricity Tariff Increases (+15%, +30%)
        for price_factor, label in [(1.15, "Tariff +15%"), (1.30, "Tariff +30%")]:
            df_pr = df_sub.copy()
            df_pr["day_ahead_price_inr_kwh"] = df_pr["day_ahead_price_inr_kwh"] * price_factor
            df_pr["real_time_price_inr_kwh"] = df_pr["real_time_price_inr_kwh"] * price_factor
            opt = StochasticOptimizer(self.battery_params, self.grid_params)
            out = opt.solve_stochastic_model(df_pr, risk_weight_lambda=0.0)
            results.append({
                "sensitivity_category": "Electricity Tariffs",
                "parameter_variation": label,
                "expected_cost_inr": round(out.expected_total_cost_inr, 2),
                "var_95_inr": round(out.var_95_cost_inr, 2),
                "cvar_95_inr": round(out.cvar_95_cost_inr, 2),
                "day_ahead_energy_kwh": round(float(np.sum(out.day_ahead_schedule_kw)), 1),
                "solve_time_sec": round(out.solve_time_sec, 3),
            })

        sens_df = pd.DataFrame(results)
        sens_csv = RESULTS_DIR / "sensitivity_results.csv"
        sens_df.to_csv(sens_csv, index=False)
        logger.info(f"Saved {len(sens_df)} sensitivity results to {sens_csv}")
        return sens_df

    @staticmethod
    def save_all_results(
        stochastic_out: OptimizationOutput,
        x_det: np.ndarray,
        eev_cost: float,
        evpi_val: float,
        ws_cost: float,
        weather_conditions: Optional[List[str]] = None,
    ) -> Dict[str, Path]:
        """Saves all required result files to data/results/."""
        saved_paths = {}

        # 1. Hourly Dispatch Schedule CSV
        hourly_df = stochastic_out.get_hourly_dataframe()
        hourly_path = RESULTS_DIR / "stochastic_hourly_schedule.csv"
        hourly_df.to_csv(hourly_path, index=False)
        saved_paths["hourly_schedule"] = hourly_path

        # 2. Scenario-Level Financials CSV
        scen_df = stochastic_out.get_scenario_costs_dataframe(weather_conditions)
        scen_path = RESULTS_DIR / "scenario_costs.csv"
        scen_df.to_csv(scen_path, index=False)
        saved_paths["scenario_costs"] = scen_path

        # 3. Deterministic Baseline Schedule CSV
        det_df = pd.DataFrame({
            "hour": list(range(24)),
            "deterministic_day_ahead_kw": np.round(x_det, 2),
            "stochastic_day_ahead_kw": np.round(stochastic_out.day_ahead_schedule_kw, 2),
            "contract_deviation_kw": np.round(stochastic_out.day_ahead_schedule_kw - x_det, 2),
        })
        det_path = RESULTS_DIR / "deterministic_baseline.csv"
        det_df.to_csv(det_path, index=False)
        saved_paths["deterministic_baseline"] = det_path

        # 4. Stochastic Metrics: VSS and EVPI
        rp_cost = stochastic_out.expected_total_cost_inr
        vss_val = max(0.0, eev_cost - rp_cost)
        vss_pct = (vss_val / eev_cost * 100.0) if eev_cost > 0 else 0.0

        vss_evpi_dict = {
            "recourse_problem_stochastic_cost_inr": round(rp_cost, 2),
            "expected_value_of_expected_solution_eev_inr": round(eev_cost, 2),
            "wait_and_see_perfect_info_cost_ws_inr": round(ws_cost, 2),
            "value_of_stochastic_solution_vss_inr": round(vss_val, 2),
            "vss_percentage_savings": round(vss_pct, 2),
            "expected_value_of_perfect_information_evpi_inr": round(evpi_val, 2),
            "evpi_percentage_of_rp": round((evpi_val / rp_cost * 100.0), 2) if rp_cost > 0 else 0.0,
            "mathematical_relationship_verified": bool(ws_cost <= rp_cost <= eev_cost + 1e-4),
        }
        vss_path = RESULTS_DIR / "vss_evpi_metrics.json"
        with open(vss_path, "w", encoding="utf-8") as f:
            json.dump(vss_evpi_dict, f, indent=2)
        saved_paths["vss_evpi"] = vss_path

        # 5. Risk Metrics JSON
        risk_dict = {
            "expected_cost_inr": round(stochastic_out.expected_total_cost_inr, 2),
            "min_scenario_cost_inr": round(stochastic_out.min_scenario_cost_inr, 2),
            "max_scenario_cost_inr": round(stochastic_out.max_scenario_cost_inr, 2),
            "std_scenario_cost_inr": round(stochastic_out.std_scenario_cost_inr, 2),
            "median_scenario_cost_inr": round(stochastic_out.median_scenario_cost_inr, 2),
            "percentile_90_cost_inr": round(stochastic_out.percentile_90_cost_inr, 2),
            "var_95_cost_inr": round(stochastic_out.var_95_cost_inr, 2),
            "cvar_95_cost_inr": round(stochastic_out.cvar_95_cost_inr, 2),
            "confidence_level_alpha": 0.95,
            "risk_parameter_lambda": stochastic_out.risk_lambda,
        }
        risk_path = RESULTS_DIR / "risk_metrics.json"
        with open(risk_path, "w", encoding="utf-8") as f:
            json.dump(risk_dict, f, indent=2)
        saved_paths["risk_metrics"] = risk_path

        # 6. Overall Optimization Summary JSON
        summary_dict = stochastic_out.get_summary_dict()
        summary_dict["vss_inr"] = round(vss_val, 2)
        summary_dict["vss_savings_pct"] = round(vss_pct, 2)
        summary_dict["evpi_inr"] = round(evpi_val, 2)
        summary_dict["deterministic_baseline_eev_inr"] = round(eev_cost, 2)
        summary_path = RESULTS_DIR / "optimization_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_dict, f, indent=2)
        saved_paths["optimization_summary"] = summary_path

        # 7. Model Config Snapshot and Solver Log
        config_snapshot = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "solver_engine": "SciPy HiGHS (Interior Point / Dual Simplex)",
            "formulation": "Two-Stage Stochastic Linear Program with Rockafellar-Uryasev Mean-CVaR",
            "decision_variables_count": len(stochastic_out.day_ahead_schedule_kw) + len(stochastic_out.matrix_g.flatten()) * 6 + 1 + len(stochastic_out.scenario_ids),
            "num_scenarios": len(stochastic_out.scenario_ids),
            "battery_capacity_kwh": 1000.0,
            "battery_efficiency_roundtrip": 0.8464,
            "grid_import_limit_kw": 1000.0,
            "is_synthetic_data": True,
            "provenance_notice": "SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA",
        }
        config_path = RESULTS_DIR / "model_config_snapshot.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_snapshot, f, indent=2)
        saved_paths["config_snapshot"] = config_path

        logger.info(f"Successfully saved all optimization results to: {RESULTS_DIR}")
        return saved_paths

