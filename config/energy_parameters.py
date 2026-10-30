"""
GRIDWISE AI - Campus Energy & Asset Configuration
Reference specifications for Solar PV, BESS, and Microgrid Interconnection.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class EnergyParameters:
    """Configurable campus microgrid physical and economic parameters."""

    # Solar PV Specification
    solar_installed_capacity_kwp: float = 800.0  # Solar installed capacity: 800 kWp
    solar_degradation_factor: float = 0.995      # Annual PV degradation factor
    inverter_efficiency: float = 0.975           # Central solar string inverter efficiency

    # Battery Energy Storage System (BESS)
    battery_capacity_kwh: float = 1000.0         # Battery capacity: 1000 kWh
    battery_max_power_kw: float = 400.0          # Max C/D power rating (0.4 C-rate)
    battery_charge_efficiency: float = 0.92      # Battery charging efficiency: 92%
    battery_discharge_efficiency: float = 0.92   # Battery discharging efficiency: 92%
    battery_initial_soc: float = 0.50            # Initial battery SOC: 50%
    battery_min_soc: float = 0.15                # Minimum depth of discharge protection
    battery_max_soc: float = 0.95                # Maximum state-of-charge upper bound
    battery_degradation_cost_inr_kwh: float = 1.85  # Degradation replacement cost per kWh cycled

    # Grid Interconnection & Utility Limits
    grid_import_limit_kw: float = 1000.0         # Maximum utility import limit (kW)
    grid_export_limit_kw: float = 500.0          # Maximum surplus feed-in limit (kW)
    peak_demand_charge_inr_kw: float = 450.0     # Monthly peak demand tariff (INR/kW-month)

    # Simulation Horizon
    simulation_interval_hours: float = 1.0       # Simulation interval: 1 hour
    simulation_horizon_hours: int = 24           # Simulation horizon: 24 hours
    annual_simulation_hours: int = 8760          # 365 days * 24 hours = 8760 records

    # Economic & Currency Reference
    currency: str = "INR"                        # Indian Rupees (INR)
    energy_unit: str = "kWh"
    power_unit: str = "kW"

    def to_dict(self) -> Dict[str, Any]:
        """Convert parameters to dictionary format."""
        return asdict(self)


# Default global instance
DEFAULT_ENERGY_PARAMS = EnergyParameters()

