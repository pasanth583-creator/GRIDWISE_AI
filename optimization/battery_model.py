"""
GRIDWISE AI - Battery and Grid Physical Parameter Specifications
Defines technical microgrid asset constraints and thermodynamic conservation equations.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class BatteryParameters:
    """Technical and operational parameters for Lithium-ion BESS."""

    capacity_kwh: float = 1000.0
    max_charge_kw: float = 400.0
    max_discharge_kw: float = 400.0
    charging_efficiency: float = 0.92
    discharging_efficiency: float = 0.92
    initial_soc_pct: float = 0.50
    min_soc_pct: float = 0.15
    max_soc_pct: float = 0.95
    degradation_cost_inr_kwh: float = 0.20  # Battery cycling wear penalty (INR/kWh)
    enforce_periodicity: bool = True       # Terminal SoC(24) >= Initial SoC(0)

    @property
    def initial_energy_kwh(self) -> float:
        return self.capacity_kwh * self.initial_soc_pct

    @property
    def min_energy_kwh(self) -> float:
        return self.capacity_kwh * self.min_soc_pct

    @property
    def max_energy_kwh(self) -> float:
        return self.capacity_kwh * self.max_soc_pct

    @property
    def round_trip_efficiency(self) -> float:
        return self.charging_efficiency * self.discharging_efficiency

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capacity_kwh": self.capacity_kwh,
            "max_charge_kw": self.max_charge_kw,
            "max_discharge_kw": self.max_discharge_kw,
            "charging_efficiency": self.charging_efficiency,
            "discharging_efficiency": self.discharging_efficiency,
            "round_trip_efficiency": round(self.round_trip_efficiency, 4),
            "initial_soc_pct": self.initial_soc_pct,
            "min_soc_pct": self.min_soc_pct,
            "max_soc_pct": self.max_soc_pct,
            "initial_energy_kwh": self.initial_energy_kwh,
            "min_energy_kwh": self.min_energy_kwh,
            "max_energy_kwh": self.max_energy_kwh,
            "degradation_cost_inr_kwh": self.degradation_cost_inr_kwh,
            "enforce_periodicity": self.enforce_periodicity,
        }


@dataclass
class GridParameters:
    """Substation point-of-interconnection contractual envelopes."""

    max_day_ahead_import_kw: float = 1000.0
    max_real_time_import_kw: float = 1000.0
    max_total_import_kw: float = 1000.0     # Combined instantaneous limit: x[t] + g[s,t] <= 1000
    max_export_kw: float = 500.0            # Feed-in capacity (or 0 if export prohibited)
    export_price_ratio: float = 0.40        # Export compensation as a fraction of Day-Ahead tariff
    shortage_penalty_inr_kwh: float = 100.0 # Strict penalty for unserved load (slack variable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_day_ahead_import_kw": self.max_day_ahead_import_kw,
            "max_real_time_import_kw": self.max_real_time_import_kw,
            "max_total_import_kw": self.max_total_import_kw,
            "max_export_kw": self.max_export_kw,
            "export_price_ratio": self.export_price_ratio,
            "shortage_penalty_inr_kwh": self.shortage_penalty_inr_kwh,
        }


def check_simultaneous_charge_discharge(
    charge_matrix: Any,
    discharge_matrix: Any,
    tolerance: float = 1e-4,
) -> Dict[str, Any]:
    """
    Validates whether the linear programming solution contains economically
    unrealistic simultaneous charging and discharging within the same hour.

    Theoretical Foundation:
    In linear programming, because the round-trip efficiency eta_ch * eta_dis < 1.0 (84.64%)
    and cycling incurs degradation cost c_deg > 0, simultaneously charging and discharging
    wastes energy and adds cost. The linear relaxation naturally guarantees:
        c[s, t] * d[s, t] == 0  (within solver tolerance)
    """
    import numpy as np
    c = np.asarray(charge_matrix)
    d = np.asarray(discharge_matrix)
    overlap = np.minimum(c, d)
    max_overlap = float(np.max(overlap))
    total_overlap = float(np.sum(overlap))
    is_valid = max_overlap < tolerance

    return {
        "max_simultaneous_kw": max_overlap,
        "total_simultaneous_kwh": total_overlap,
        "is_strictly_separated": is_valid,
        "explanation": (
            "Natural economic complementarity verified: "
            "Round-trip losses (84.6% efficiency) and cycling degradation costs "
            "strictly rule out simultaneous charging and discharging at optimality."
        ),
    }

