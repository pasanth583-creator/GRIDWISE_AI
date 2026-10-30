"""
GRIDWISE AI - Linear Programming Solver Interface
Executes SciPy HiGHS interior-point / simplex solvers with numerical verification.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import time
import logging
import numpy as np
from scipy.optimize import linprog
from scipy import sparse

logger = logging.getLogger(__name__)


class OptimizationSolverError(Exception):
    """Raised when the optimization problem is infeasible, unbounded, or exceeds limits."""
    pass


@dataclass
class SolverResult:
    """Encapsulates raw LP solver output, status, and diagnostic residuals."""

    success: bool
    status_code: int
    status_message: str
    objective_value: float
    solution_vector: np.ndarray
    solve_time_sec: float
    num_iterations: int
    max_eq_residual: float
    max_ub_violation: float
    solver_name: str = "SciPy HiGHS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status_code": self.status_code,
            "status_message": self.status_message,
            "objective_value": round(float(self.objective_value), 2),
            "solve_time_sec": round(float(self.solve_time_sec), 4),
            "num_iterations": self.num_iterations,
            "max_eq_residual": float(self.max_eq_residual),
            "max_ub_violation": float(self.max_ub_violation),
            "solver_name": self.solver_name,
        }


class LinearSolver:
    """Wrapper around SciPy HiGHS linear programming solver."""

    @staticmethod
    def solve_lp(
        c: np.ndarray,
        A_eq: sparse.csr_matrix,
        b_eq: np.ndarray,
        A_ub: sparse.csr_matrix,
        b_ub: np.ndarray,
        bounds: List[tuple],
        time_limit_sec: float = 60.0,
        presolve: bool = True,
        feasibility_tol: float = 1e-5,
    ) -> SolverResult:
        """
        Solves linear program min c^T v subject to A_eq v == b_eq, A_ub v <= b_ub, l <= v <= u.
        """
        logger.info(
            f"Solving LP via HiGHS: {len(c)} vars, {A_eq.shape[0]} eq constraints, "
            f"{A_ub.shape[0]} ub constraints."
        )

        options = {
            "time_limit": time_limit_sec,
            "presolve": presolve,
            "primal_feasibility_tolerance": feasibility_tol,
            "dual_feasibility_tolerance": feasibility_tol,
        }

        t_start = time.perf_counter()
        res = linprog(
            c=c,
            A_ub=A_ub,
            b_ub=b_ub,
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=bounds,
            method="highs",
            options=options,
        )
        t_elapsed = time.perf_counter() - t_start

        if not res.success:
            err_msg = (
                f"HiGHS LP solve failed with code {res.status}: {res.message}. "
                f"Elapsed: {t_elapsed:.2f}s."
            )
            logger.error(err_msg)
            raise OptimizationSolverError(err_msg)

        sol = res.x

        # Compute diagnostic residuals
        # Max equality residual: || A_eq * x - b_eq ||_inf
        eq_residuals = A_eq.dot(sol) - b_eq
        max_eq_res = float(np.max(np.abs(eq_residuals))) if len(eq_residuals) > 0 else 0.0

        # Max inequality violation: max(0, A_ub * x - b_ub)
        ub_violations = A_ub.dot(sol) - b_ub
        max_ub_viol = float(np.max(np.maximum(0.0, ub_violations))) if len(ub_violations) > 0 else 0.0

        logger.info(
            f"HiGHS LP solve SUCCESS: Obj={res.fun:.2f}, Time={t_elapsed:.3f}s, "
            f"Max Eq Res={max_eq_res:.2e}, Max Ub Viol={max_ub_viol:.2e}"
        )

        return SolverResult(
            success=True,
            status_code=int(res.status),
            status_message=str(res.message),
            objective_value=float(res.fun),
            solution_vector=sol,
            solve_time_sec=t_elapsed,
            num_iterations=int(getattr(res, "nit", 0)),
            max_eq_residual=max_eq_res,
            max_ub_violation=max_ub_viol,
        )

