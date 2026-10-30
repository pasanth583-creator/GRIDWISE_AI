"""
GRIDWISE AI - Domain Models
Data transfer objects and domain schemas for the Campus Solar + Battery Microgrid.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class MicrogridConfig:
    """Campus Microgrid Physical and Operational Specifications."""

    id: Optional[int] = 1
    config_name: str = "Campus Main Microgrid"
    pv_capacity_kw: float = 800.0
    bess_capacity_kwh: float = 1000.0
    bess_max_power_kw: float = 400.0
    bess_charge_efficiency: float = 0.92
    bess_discharge_efficiency: float = 0.92
    min_soc: float = 0.15
    max_soc: float = 0.95
    initial_soc: float = 0.50
    grid_import_limit_kw: float = 1000.0
    grid_export_limit_kw: float = 500.0
    demand_charge_rate: float = 14.50

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DayAheadHourlyInput:
    """Hourly input parameters: market prices, expected solar, and campus load."""

    hour: int
    buy_price_per_kwh: float
    sell_price_per_kwh: float
    expected_solar_kw: float
    expected_load_kw: float
    solar_p10_kw: float = 0.0
    solar_p90_kw: float = 0.0
    load_p10_kw: float = 0.0
    load_p90_kw: float = 0.0
    tariff_period: str = "Off-Peak"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HourlyDispatchSchedule:
    """Optimal energy procurement and dispatch decision for a single hour."""

    hour: int
    grid_import_kw: float = 0.0
    grid_export_kw: float = 0.0
    solar_used_kw: float = 0.0
    solar_curtailed_kw: float = 0.0
    bess_charge_kw: float = 0.0
    bess_discharge_kw: float = 0.0
    bess_soc_kwh: float = 600.0
    bess_soc_pct: float = 50.0
    campus_load_kw: float = 0.0
    hourly_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationRunSummary:
    """Metadata and high-level objective results for a stochastic optimization run."""

    run_uuid: str
    run_name: str
    run_date: str
    status: str = "INITIALIZED"
    formulation_type: str = "Two-Stage Stochastic"
    num_scenarios: int = 50
    solver_name: str = "SciPy HiGHS / Interior-Point"
    total_procurement_cost: float = 0.0
    baseline_cost: float = 0.0
    cost_savings_pct: float = 0.0
    total_solar_used_kwh: float = 0.0
    total_grid_imported_kwh: float = 0.0
    total_grid_exported_kwh: float = 0.0
    total_battery_cycled_kwh: float = 0.0
    solver_runtime_sec: float = 0.0
    notes: Optional[str] = None
    created_at: Optional[str] = None
    schedule: List[HourlyDispatchSchedule] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["schedule"] = [s.to_dict() if hasattr(s, "to_dict") else s for s in self.schedule]
        return res


__all__ = [
    "MicrogridConfig",
    "DayAheadHourlyInput",
    "HourlyDispatchSchedule",
    "OptimizationRunSummary",
]

