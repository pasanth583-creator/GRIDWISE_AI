"""
GRIDWISE AI - Optimization Architecture Module
Stochastic Optimization of Day-Ahead Energy Procurement for a Campus Solar + Battery Microgrid.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from optimization.scenario_loader import ScenarioLoader, ScenarioValidationError
from optimization.battery_model import BatteryParameters, GridParameters, check_simultaneous_charge_discharge
from optimization.objective import ObjectiveBuilder
from optimization.constraints import ConstraintBuilder
from optimization.solver import LinearSolver, SolverResult, OptimizationSolverError
from optimization.optimization_results import OptimizationOutput, ResultsParser
from optimization.stochastic_model import StochasticOptimizer


class SolverMethod(Enum):
    HIGHS_INTERIOR_POINT = "SciPy HiGHS (Interior Point)"
    HIGHS_SIMPLEX = "SciPy HiGHS (Dual Simplex)"


class FormulationType(Enum):
    DETERMINISTIC_BASELINE = "Deterministic Day-Ahead"
    TWO_STAGE_STOCHASTIC = "Two-Stage Stochastic Programming"
    RISK_AVERSE_CVAR = "Risk-Averse Stochastic (CVaR)"


@dataclass
class OptimizationParameters:
    """Mathematical formulation parameter specification."""

    formulation: FormulationType = FormulationType.TWO_STAGE_STOCHASTIC
    num_scenarios: int = 500
    confidence_alpha: float = 0.95
    risk_weight_lambda: float = 0.0
    enable_battery_degradation_penalty: bool = True
    battery_degradation_cost_per_kwh: float = 0.20
    solver_method: SolverMethod = SolverMethod.HIGHS_INTERIOR_POINT


__all__ = [
    "StochasticOptimizer",
    "OptimizationOutput",
    "BatteryParameters",
    "GridParameters",
    "ScenarioLoader",
    "ScenarioValidationError",
    "LinearSolver",
    "SolverResult",
    "OptimizationSolverError",
    "ObjectiveBuilder",
    "ConstraintBuilder",
    "ResultsParser",
    "check_simultaneous_charge_discharge",
    "FormulationType",
    "SolverMethod",
    "OptimizationParameters",
]
