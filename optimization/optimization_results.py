"""
GRIDWISE AI - Optimization Results Parser and Diagnostics
Extracts hourly dispatch schedules, scenario cost distributions, and tail risk metrics.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from optimization.battery_model import BatteryParameters, GridParameters, check_simultaneous_charge_discharge
from optimization.solver import SolverResult


@dataclass
class OptimizationOutput:
    """Structured results parsed from Two-Stage Stochastic LP solution."""

    success: bool
    expected_total_cost_inr: float
    day_ahead_schedule_kw: np.ndarray      # Shape: (24,)
    expected_real_time_import_kw: np.ndarray# Shape: (24,)
    expected_battery_charge_kw: np.ndarray  # Shape: (24,)
    expected_battery_discharge_kw: np.ndarray# Shape: (24,)
    expected_battery_soc_kwh: np.ndarray    # Shape: (24,)
    expected_battery_soc_pct: np.ndarray    # Shape: (24,)
    expected_export_kw: np.ndarray          # Shape: (24,)
    expected_shortage_kw: np.ndarray        # Shape: (24,)

    scenario_ids: List[str]
    scenario_probabilities: np.ndarray      # Shape: (N,)
    scenario_costs_inr: np.ndarray          # Shape: (N,)

    # Risk metrics
    min_scenario_cost_inr: float
    max_scenario_cost_inr: float
    std_scenario_cost_inr: float
    median_scenario_cost_inr: float
    percentile_90_cost_inr: float
    var_95_cost_inr: float
    cvar_95_cost_inr: float

    # Raw matrices
    matrix_g: np.ndarray                    # Real-time purchase: (N, 24)
    matrix_c: np.ndarray                    # Charge: (N, 24)
    matrix_d: np.ndarray                    # Discharge: (N, 24)
    matrix_e: np.ndarray                    # Export: (N, 24)
    matrix_b: np.ndarray                    # SoC energy: (N, 24)

    # Diagnostic metadata
    solve_time_sec: float
    max_eq_residual: float
    max_ub_violation: float
    simultaneous_check: Dict[str, Any]
    risk_lambda: float = 0.0

    def get_hourly_dataframe(self) -> pd.DataFrame:
        """Constructs 24-hour dispatch schedule DataFrame."""
        hours = list(range(24))
        df = pd.DataFrame({
            "hour": hours,
            "day_ahead_procurement_kw": np.round(self.day_ahead_schedule_kw, 2),
            "expected_real_time_kw": np.round(self.expected_real_time_import_kw, 2),
            "expected_battery_charge_kw": np.round(self.expected_battery_charge_kw, 2),
            "expected_battery_discharge_kw": np.round(self.expected_battery_discharge_kw, 2),
            "expected_battery_soc_kwh": np.round(self.expected_battery_soc_kwh, 2),
            "expected_battery_soc_pct": np.round(self.expected_battery_soc_pct, 1),
            "expected_export_kw": np.round(self.expected_export_kw, 2),
            "expected_shortage_kw": np.round(self.expected_shortage_kw, 2),
            "total_grid_import_kw": np.round(self.day_ahead_schedule_kw + self.expected_real_time_import_kw, 2),
        })
        return df

    def get_scenario_costs_dataframe(self, weather_conditions: Optional[List[str]] = None) -> pd.DataFrame:
        """Constructs scenario-level financial breakdown DataFrame."""
        df = pd.DataFrame({
            "scenario_id": self.scenario_ids,
            "probability": np.round(self.scenario_probabilities, 6),
            "scenario_cost_inr": np.round(self.scenario_costs_inr, 2),
        })
        if weather_conditions is not None and len(weather_conditions) == len(self.scenario_ids):
            df["weather_condition"] = weather_conditions
        return df

    def get_summary_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable operational and financial executive summary."""
        total_da_energy_kwh = float(np.sum(self.day_ahead_schedule_kw))
        total_rt_energy_kwh = float(np.sum(self.expected_real_time_import_kw))
        total_throughput_kwh = float(np.sum(self.expected_battery_discharge_kw))
        eq_cycles = total_throughput_kwh / 1000.0  # Normalized to 1000 kWh capacity

        return {
            "status": "OPTIMAL",
            "solver": "SciPy HiGHS (Interior Point)",
            "solve_time_seconds": round(self.solve_time_sec, 4),
            "risk_parameter_lambda": round(self.risk_lambda, 2),
            "num_scenarios_evaluated": len(self.scenario_ids),
            "expected_total_cost_inr": round(self.expected_total_cost_inr, 2),
            "day_ahead_energy_kwh": round(total_da_energy_kwh, 1),
            "expected_real_time_energy_kwh": round(total_rt_energy_kwh, 1),
            "battery_daily_cycles": round(eq_cycles, 2),
            "battery_throughput_kwh": round(total_throughput_kwh, 1),
            "peak_grid_import_kw": round(float(np.max(self.day_ahead_schedule_kw + self.expected_real_time_import_kw)), 1),
            "max_equality_residual": float(self.max_eq_residual),
            "max_inequality_violation": float(self.max_ub_violation),
            "simultaneous_charging_kw": self.simultaneous_check["max_simultaneous_kw"],
            "risk_metrics": {
                "expected_cost_inr": round(self.expected_total_cost_inr, 2),
                "min_scenario_cost_inr": round(self.min_scenario_cost_inr, 2),
                "max_scenario_cost_inr": round(self.max_scenario_cost_inr, 2),
                "std_scenario_cost_inr": round(self.std_scenario_cost_inr, 2),
                "median_scenario_cost_inr": round(self.median_scenario_cost_inr, 2),
                "percentile_90_cost_inr": round(self.percentile_90_cost_inr, 2),
                "var_95_cost_inr": round(self.var_95_cost_inr, 2),
                "cvar_95_cost_inr": round(self.cvar_95_cost_inr, 2),
            },
        }


class ResultsParser:
    """Extracts and verifies technical dispatch matrices from LP primal solution."""

    @staticmethod
    def parse_solution(
        solver_res: SolverResult,
        idx_map: Dict[str, Any],
        scenario_ids: List[str],
        probabilities: np.ndarray,
        da_prices_24h: np.ndarray,
        rt_prices_matrix: np.ndarray,
        battery_params: BatteryParameters,
        grid_params: GridParameters,
        risk_weight_lambda: float = 0.0,
    ) -> OptimizationOutput:
        """Parses the raw decision vector into high-level dispatch structures."""
        sol = solver_res.solution_vector
        N = idx_map["N"]
        T = idx_map["T"]

        # 1. Day-ahead schedule x[t]
        x_da = sol[idx_map["x"]]

        # 2. Reshape second-stage decision matrices: (N, 24)
        g_mat = np.zeros((N, T), dtype=float)
        c_mat = np.zeros((N, T), dtype=float)
        d_mat = np.zeros((N, T), dtype=float)
        e_mat = np.zeros((N, T), dtype=float)
        b_mat = np.zeros((N, T), dtype=float)
        sh_mat = np.zeros((N, T), dtype=float)

        for s in range(N):
            g_idx = idx_map["g_start"] + s * T
            c_idx = idx_map["c_start"] + s * T
            d_idx = idx_map["d_start"] + s * T
            e_idx = idx_map["e_start"] + s * T
            b_idx = idx_map["b_start"] + s * T
            sh_idx = idx_map["short_start"] + s * T

            g_mat[s, :] = sol[g_idx : g_idx + T]
            c_mat[s, :] = sol[c_idx : c_idx + T]
            d_mat[s, :] = sol[d_idx : d_idx + T]
            e_mat[s, :] = sol[e_idx : e_idx + T]
            b_mat[s, :] = sol[b_idx : b_idx + T]
            sh_mat[s, :] = sol[sh_idx : sh_idx + T]

        # Check simultaneous charging and discharging
        simult_check = check_simultaneous_charge_discharge(c_mat, d_mat)

        # 3. Compute probability-weighted expectations
        probs = probabilities
        exp_g = np.sum(g_mat * probs[:, np.newaxis], axis=0)
        exp_c = np.sum(c_mat * probs[:, np.newaxis], axis=0)
        exp_d = np.sum(d_mat * probs[:, np.newaxis], axis=0)
        exp_e = np.sum(e_mat * probs[:, np.newaxis], axis=0)
        exp_b = np.sum(b_mat * probs[:, np.newaxis], axis=0)
        exp_sh = np.sum(sh_mat * probs[:, np.newaxis], axis=0)
        exp_soc_pct = (exp_b / battery_params.capacity_kwh) * 100.0

        # 4. Calculate scenario-specific costs (INR)
        # Cost_s = sum_t [ c_DA * x + c_RT * g - c_exp * e + c_deg * (c + d) + c_short * sh ]
        c_deg = battery_params.degradation_cost_inr_kwh
        c_short = grid_params.shortage_penalty_inr_kwh
        exp_ratio = grid_params.export_price_ratio

        da_spend = float(np.sum(da_prices_24h * x_da))
        scenario_costs = np.zeros(N, dtype=float)

        for s in range(N):
            rt_spend = float(np.sum(rt_prices_matrix[s, :] * g_mat[s, :]))
            exp_rev = float(np.sum(da_prices_24h * exp_ratio * e_mat[s, :]))
            deg_spend = float(np.sum(c_deg * (c_mat[s, :] + d_mat[s, :])))
            sh_spend = float(np.sum(c_short * sh_mat[s, :]))
            scenario_costs[s] = da_spend + rt_spend - exp_rev + deg_spend + sh_spend

        expected_cost = float(np.sum(probs * scenario_costs))

        # 5. Risk metrics calculation
        min_cost = float(np.min(scenario_costs))
        max_cost = float(np.max(scenario_costs))
        mean_cost = expected_cost
        std_cost = float(np.sqrt(np.sum(probs * (scenario_costs - mean_cost) ** 2)))

        # Weighted percentiles & CVaR (alpha = 0.95)
        # Sort costs
        sort_idx = np.argsort(scenario_costs)
        sorted_costs = scenario_costs[sort_idx]
        sorted_probs = probs[sort_idx]
        cum_probs = np.cumsum(sorted_probs)

        # Median (50th percentile)
        med_idx = np.searchsorted(cum_probs, 0.50)
        median_cost = float(sorted_costs[min(med_idx, N - 1)])

        # 90th percentile
        p90_idx = np.searchsorted(cum_probs, 0.90)
        p90_cost = float(sorted_costs[min(p90_idx, N - 1)])

        # 95th percentile (VaR_95)
        var_idx = np.searchsorted(cum_probs, 0.95)
        var_95_cost = float(sorted_costs[min(var_idx, N - 1)])

        # CVaR 95% = Conditional expectation of costs >= VaR_95
        tail_mask = cum_probs >= 0.95
        if np.any(tail_mask):
            tail_weights = sorted_probs[tail_mask]
            tail_costs = sorted_costs[tail_mask]
            cvar_95_cost = float(np.sum(tail_weights * tail_costs) / np.sum(tail_weights))
        else:
            cvar_95_cost = var_95_cost

        return OptimizationOutput(
            success=True,
            expected_total_cost_inr=expected_cost,
            day_ahead_schedule_kw=x_da,
            expected_real_time_import_kw=exp_g,
            expected_battery_charge_kw=exp_c,
            expected_battery_discharge_kw=exp_d,
            expected_battery_soc_kwh=exp_b,
            expected_battery_soc_pct=exp_soc_pct,
            expected_export_kw=exp_e,
            expected_shortage_kw=exp_sh,
            scenario_ids=scenario_ids,
            scenario_probabilities=probs,
            scenario_costs_inr=scenario_costs,
            min_scenario_cost_inr=min_cost,
            max_scenario_cost_inr=max_cost,
            std_scenario_cost_inr=std_cost,
            median_scenario_cost_inr=median_cost,
            percentile_90_cost_inr=p90_cost,
            var_95_cost_inr=var_95_cost,
            cvar_95_cost_inr=cvar_95_cost,
            matrix_g=g_mat,
            matrix_c=c_mat,
            matrix_d=d_mat,
            matrix_e=e_mat,
            matrix_b=b_mat,
            solve_time_sec=solver_res.solve_time_sec,
            max_eq_residual=solver_res.max_eq_residual,
            max_ub_violation=solver_res.max_ub_violation,
            simultaneous_check=simult_check,
            risk_lambda=risk_weight_lambda,
        )

