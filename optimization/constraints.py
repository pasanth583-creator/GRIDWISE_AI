"""
GRIDWISE AI - Constraint Matrix Assembly
Constructs high-performance sparse linear constraint matrices and bounds for Two-Stage Stochastic LP.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
from scipy import sparse

from optimization.battery_model import BatteryParameters, GridParameters


class ConstraintBuilder:
    """Constructs equality/inequality constraint matrices and variable bounds."""

    @staticmethod
    def build_constraints(
        num_scenarios: int,
        demand_matrix: np.ndarray,      # Shape: (N, 24)
        solar_matrix: np.ndarray,       # Shape: (N, 24)
        da_prices_24h: np.ndarray,      # Shape: (24,)
        rt_prices_matrix: np.ndarray,   # Shape: (N, 24)
        battery_params: BatteryParameters,
        grid_params: GridParameters,
        idx_map: Dict[str, Any],
        risk_weight_lambda: float = 0.0,
        fixed_x_da: np.ndarray = None,  # If provided, fixes x[t] = fixed_x_da[t] (for EEV evaluation)
    ) -> Tuple[sparse.csr_matrix, np.ndarray, sparse.csr_matrix, np.ndarray, List[Tuple[float, float]]]:
        """
        Builds sparse equality (A_eq, b_eq), inequality (A_ub, b_ub), and variable bounds.
        """
        N = num_scenarios
        T = idx_map["T"]
        total_vars = idx_map["total_vars"]
        has_cvar = (risk_weight_lambda > 0.0)

        eta_ch = battery_params.charging_efficiency
        inv_eta_dis = 1.0 / battery_params.discharging_efficiency
        b_init = battery_params.initial_energy_kwh

        # ------------------------------------------------------------------
        # 1. EQUALITY CONSTRAINTS (A_eq * v == b_eq)
        #    a) Energy Balance: T * N rows
        #    b) Battery Dynamics: T * N rows
        #    c) Fixed x[t] (if fixed_x_da provided): T rows
        # ------------------------------------------------------------------
        eq_rows, eq_cols, eq_vals = [], [], []
        b_eq_list = []
        row_eq = 0

        # a) Energy Balance Constraint:
        # x[t] + g[s, t] + d[s, t] + short[s, t] - c[s, t] - e[s, t] = Demand[s, t] - Solar[s, t]
        for s in range(N):
            g_idx_base = idx_map["g_start"] + s * T
            c_idx_base = idx_map["c_start"] + s * T
            d_idx_base = idx_map["d_start"] + s * T
            e_idx_base = idx_map["e_start"] + s * T
            sh_idx_base = idx_map["short_start"] + s * T

            for t in range(T):
                # x[t]
                eq_rows.append(row_eq)
                eq_cols.append(t)
                eq_vals.append(1.0)

                # g[s, t]
                eq_rows.append(row_eq)
                eq_cols.append(g_idx_base + t)
                eq_vals.append(1.0)

                # d[s, t]
                eq_rows.append(row_eq)
                eq_cols.append(d_idx_base + t)
                eq_vals.append(1.0)

                # short[s, t]
                eq_rows.append(row_eq)
                eq_cols.append(sh_idx_base + t)
                eq_vals.append(1.0)

                # - c[s, t]
                eq_rows.append(row_eq)
                eq_cols.append(c_idx_base + t)
                eq_vals.append(-1.0)

                # - e[s, t]
                eq_rows.append(row_eq)
                eq_cols.append(e_idx_base + t)
                eq_vals.append(-1.0)

                rhs_net_demand = float(demand_matrix[s, t] - solar_matrix[s, t])
                b_eq_list.append(rhs_net_demand)
                row_eq += 1

        # b) Battery Storage Dynamics:
        # b[s, t] - b[s, t-1] - eta_ch * c[s, t] + (1 / eta_dis) * d[s, t] == 0
        # for t = 0: b[s, 0] - eta_ch * c[s, 0] + (1 / eta_dis) * d[s, 0] == b_init
        for s in range(N):
            c_idx_base = idx_map["c_start"] + s * T
            d_idx_base = idx_map["d_start"] + s * T
            b_idx_base = idx_map["b_start"] + s * T

            for t in range(T):
                # b[s, t]
                eq_rows.append(row_eq)
                eq_cols.append(b_idx_base + t)
                eq_vals.append(1.0)

                # - b[s, t-1]
                if t > 0:
                    eq_rows.append(row_eq)
                    eq_cols.append(b_idx_base + t - 1)
                    eq_vals.append(-1.0)
                    b_eq_list.append(0.0)
                else:
                    b_eq_list.append(b_init)

                # - eta_ch * c[s, t]
                eq_rows.append(row_eq)
                eq_cols.append(c_idx_base + t)
                eq_vals.append(-eta_ch)

                # + (1 / eta_dis) * d[s, t]
                eq_rows.append(row_eq)
                eq_cols.append(d_idx_base + t)
                eq_vals.append(inv_eta_dis)

                row_eq += 1

        # c) If fixed_x_da is provided (for EEV baseline simulation)
        if fixed_x_da is not None:
            for t in range(T):
                eq_rows.append(row_eq)
                eq_cols.append(t)
                eq_vals.append(1.0)
                b_eq_list.append(float(fixed_x_da[t]))
                row_eq += 1

        A_eq = sparse.csr_matrix((eq_vals, (eq_rows, eq_cols)), shape=(row_eq, total_vars), dtype=float)
        b_eq = np.array(b_eq_list, dtype=float)

        # ------------------------------------------------------------------
        # 2. INEQUALITY CONSTRAINTS (A_ub * v <= b_ub)
        #    a) Combined Grid Import Limit: x[t] + g[s, t] <= P_grid_max  (N * T rows)
        #    b) Battery Periodicity: - b[s, 23] <= - b_init               (N rows)
        #    c) CVaR Tail Loss: Cost_s - zeta - u_s <= 0                   (N rows if has_cvar)
        # ------------------------------------------------------------------
        ub_rows, ub_cols, ub_vals = [], [], []
        b_ub_list = []
        row_ub = 0

        # a) Total Grid Import Envelope: x[t] + g[s, t] <= max_total_import_kw
        p_grid_limit = grid_params.max_total_import_kw
        for s in range(N):
            g_idx_base = idx_map["g_start"] + s * T
            for t in range(T):
                ub_rows.append(row_ub)
                ub_cols.append(t)
                ub_vals.append(1.0)

                ub_rows.append(row_ub)
                ub_cols.append(g_idx_base + t)
                ub_vals.append(1.0)

                b_ub_list.append(p_grid_limit)
                row_ub += 1

        # b) Battery Terminal Energy Periodicity: b[s, 23] >= b_init  ==>  - b[s, 23] <= - b_init
        if battery_params.enforce_periodicity:
            for s in range(N):
                b_terminal_idx = idx_map["b_start"] + s * T + (T - 1)
                ub_rows.append(row_ub)
                ub_cols.append(b_terminal_idx)
                ub_vals.append(-1.0)
                b_ub_list.append(-b_init)
                row_ub += 1

        # c) CVaR Shortfall Constraints: Cost_s - zeta - u_s <= 0
        if has_cvar:
            zeta_idx = idx_map["zeta"]
            u_start = idx_map["u_start"]
            c_deg = battery_params.degradation_cost_inr_kwh
            c_short = grid_params.shortage_penalty_inr_kwh
            exp_ratio = grid_params.export_price_ratio

            for s in range(N):
                g_idx_base = idx_map["g_start"] + s * T
                c_idx_base = idx_map["c_start"] + s * T
                d_idx_base = idx_map["d_start"] + s * T
                e_idx_base = idx_map["e_start"] + s * T
                sh_idx_base = idx_map["short_start"] + s * T

                # Sum over t of x[t] * c_DA[t]
                for t in range(T):
                    ub_rows.append(row_ub)
                    ub_cols.append(t)
                    ub_vals.append(float(da_prices_24h[t]))

                # Sum over t of g[s, t] * c_RT[s, t]
                for t in range(T):
                    ub_rows.append(row_ub)
                    ub_cols.append(g_idx_base + t)
                    ub_vals.append(float(rt_prices_matrix[s, t]))

                # Sum over t of c[s, t] * c_deg
                for t in range(T):
                    ub_rows.append(row_ub)
                    ub_cols.append(c_idx_base + t)
                    ub_vals.append(c_deg)

                # Sum over t of d[s, t] * c_deg
                for t in range(T):
                    ub_rows.append(row_ub)
                    ub_cols.append(d_idx_base + t)
                    ub_vals.append(c_deg)

                # Sum over t of - e[s, t] * (c_DA[t] * exp_ratio)
                for t in range(T):
                    ub_rows.append(row_ub)
                    ub_cols.append(e_idx_base + t)
                    ub_vals.append(-float(da_prices_24h[t] * exp_ratio))

                # Sum over t of short[s, t] * c_short
                for t in range(T):
                    ub_rows.append(row_ub)
                    ub_cols.append(sh_idx_base + t)
                    ub_vals.append(c_short)

                # - zeta
                ub_rows.append(row_ub)
                ub_cols.append(zeta_idx)
                ub_vals.append(-1.0)

                # - u_s
                ub_rows.append(row_ub)
                ub_cols.append(u_start + s)
                ub_vals.append(-1.0)

                b_ub_list.append(0.0)
                row_ub += 1

        A_ub = sparse.csr_matrix((ub_vals, (ub_rows, ub_cols)), shape=(row_ub, total_vars), dtype=float)
        b_ub = np.array(b_ub_list, dtype=float)

        # ------------------------------------------------------------------
        # 3. VARIABLE BOUNDS [(lower, upper), ...]
        # ------------------------------------------------------------------
        bounds = [(0.0, None)] * total_vars

        # x[t] bounds: [0, max_day_ahead_import_kw]
        for t in range(T):
            bounds[t] = (0.0, grid_params.max_day_ahead_import_kw)

        # Recourse variable bounds
        for s in range(N):
            g_base = idx_map["g_start"] + s * T
            c_base = idx_map["c_start"] + s * T
            d_base = idx_map["d_start"] + s * T
            e_base = idx_map["e_start"] + s * T
            b_base = idx_map["b_start"] + s * T
            sh_base = idx_map["short_start"] + s * T

            for t in range(T):
                bounds[g_base + t] = (0.0, grid_params.max_real_time_import_kw)
                bounds[c_base + t] = (0.0, battery_params.max_charge_kw)
                bounds[d_base + t] = (0.0, battery_params.max_discharge_kw)
                bounds[e_base + t] = (0.0, grid_params.max_export_kw)
                bounds[b_base + t] = (battery_params.min_energy_kwh, battery_params.max_energy_kwh)
                bounds[sh_base + t] = (0.0, None)

        if has_cvar:
            # zeta is unbounded (Value-at-Risk threshold)
            bounds[idx_map["zeta"]] = (None, None)
            # u_s >= 0
            u_start = idx_map["u_start"]
            for s in range(N):
                bounds[u_start + s] = (0.0, None)

        return A_eq, b_eq, A_ub, b_ub, bounds

