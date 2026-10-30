"""
GRIDWISE AI - Objective Function Construction
Builds probability-weighted expected cost vectors and Mean-CVaR risk formulations.
"""

from typing import Dict, Any, Optional
import numpy as np
from optimization.battery_model import BatteryParameters, GridParameters


class ObjectiveBuilder:
    """Constructs linear objective coefficients for Two-Stage Stochastic Microgrid LP."""

    @staticmethod
    def build_objective_vector(
        num_scenarios: int,
        probabilities: np.ndarray,
        da_prices_24h: np.ndarray,
        rt_prices_matrix: np.ndarray,
        battery_params: BatteryParameters,
        grid_params: GridParameters,
        risk_weight_lambda: float = 0.0,
        confidence_alpha: float = 0.95,
        horizon_hours: int = 24,
    ) -> Tuple_c:
        """
        Builds the 1D objective coefficient array c such that min c^T v.

        Returns
        -------
        Tuple_c: (c_vector, index_map)
        """
        N = num_scenarios
        T = horizon_hours
        lam = float(risk_weight_lambda)
        alpha = float(confidence_alpha)

        # Build index mapping
        idx_map = {
            "T": T,
            "N": N,
            "has_cvar": (lam > 0.0),
            "x": slice(0, T),
        }
        
        offset = T
        # 6 variables per scenario-hour: g, c, d, e, b, s_short
        idx_map["g_start"] = offset
        idx_map["c_start"] = offset + N * T
        idx_map["d_start"] = offset + 2 * N * T
        idx_map["e_start"] = offset + 3 * N * T
        idx_map["b_start"] = offset + 4 * N * T
        idx_map["short_start"] = offset + 5 * N * T
        offset += 6 * N * T

        if lam > 0.0:
            idx_map["zeta"] = offset
            offset += 1
            idx_map["u_start"] = offset
            offset += N
        else:
            idx_map["zeta"] = None
            idx_map["u_start"] = None

        total_vars = offset
        idx_map["total_vars"] = total_vars

        c = np.zeros(total_vars, dtype=float)

        # 1. First-Stage Day-Ahead Electricity Purchase: (1 - lambda) * c_DA[t]
        c[idx_map["x"]] = (1.0 - lam) * da_prices_24h

        # 2. Second-Stage Recourse Variables for each scenario s and hour t
        probs = probabilities
        c_deg = battery_params.degradation_cost_inr_kwh
        c_short = grid_params.shortage_penalty_inr_kwh
        exp_ratio = grid_params.export_price_ratio

        for s in range(N):
            pi_s = probs[s]
            weight = (1.0 - lam) * pi_s

            # Real-time grid purchase: weight * c_RT[s, t]
            g_idx = idx_map["g_start"] + s * T
            c[g_idx : g_idx + T] = weight * rt_prices_matrix[s, :]

            # Battery charging wear cost: weight * c_deg
            c_idx = idx_map["c_start"] + s * T
            c[c_idx : c_idx + T] = weight * c_deg

            # Battery discharging wear cost: weight * c_deg
            d_idx = idx_map["d_start"] + s * T
            c[d_idx : d_idx + T] = weight * c_deg

            # Export revenue (negative cost): - weight * (export_ratio * c_DA[t])
            e_idx = idx_map["e_start"] + s * T
            c[e_idx : e_idx + T] = - weight * (da_prices_24h * exp_ratio)

            # Stored energy b[s, t]: 0 in objective
            b_idx = idx_map["b_start"] + s * T
            c[b_idx : b_idx + T] = 0.0

            # Shortage unserved load penalty: weight * c_short
            sh_idx = idx_map["short_start"] + s * T
            c[sh_idx : sh_idx + T] = weight * c_short

        # 3. Risk-Averse CVaR Terms (Rockafellar & Uryasev)
        if lam > 0.0:
            # Objective term: + lambda * [ zeta + (1 / (1 - alpha)) * sum_s (pi_s * u_s) ]
            zeta_idx = idx_map["zeta"]
            c[zeta_idx] = lam * 1.0

            u_start = idx_map["u_start"]
            for s in range(N):
                c[u_start + s] = lam * (probs[s] / (1.0 - alpha))

        return c, idx_map


Tuple_c = tuple

