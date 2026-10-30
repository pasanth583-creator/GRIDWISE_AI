"""
GRIDWISE AI - Scenario Generation Parameters
Configurable assumptions for Weather, Solar, Demand, and Price Uncertainty.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class ScenarioParameters:
    """Configurable parameters for generating 500 stochastic scenarios."""

    num_scenarios: int = 500
    random_seed: int = 42

    # Weather Condition Probabilities (Sum must equal 1.0)
    weather_probabilities: Dict[str, float] = field(default_factory=lambda: {
        "Sunny": 0.35,
        "Partly Cloudy": 0.30,
        "Cloudy": 0.20,
        "Rainy": 0.15,
    })

    # Weather Properties by Condition
    weather_profiles: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "Sunny": {
            "cloud_cover_min": 0.05,
            "cloud_cover_max": 0.20,
            "solar_multiplier_min": 1.05,
            "solar_multiplier_max": 1.25,
            "temp_mean": 32.0,
            "temp_std": 2.5,
            "irradiance_multiplier_min": 1.05,
            "irradiance_multiplier_max": 1.25,
        },
        "Partly Cloudy": {
            "cloud_cover_min": 0.25,
            "cloud_cover_max": 0.50,
            "solar_multiplier_min": 0.75,
            "solar_multiplier_max": 1.00,
            "temp_mean": 28.0,
            "temp_std": 2.0,
            "irradiance_multiplier_min": 0.75,
            "irradiance_multiplier_max": 1.00,
        },
        "Cloudy": {
            "cloud_cover_min": 0.55,
            "cloud_cover_max": 0.80,
            "solar_multiplier_min": 0.40,
            "solar_multiplier_max": 0.70,
            "temp_mean": 25.0,
            "temp_std": 1.8,
            "irradiance_multiplier_min": 0.40,
            "irradiance_multiplier_max": 0.70,
        },
        "Rainy": {
            "cloud_cover_min": 0.80,
            "cloud_cover_max": 0.98,
            "solar_multiplier_min": 0.15,
            "solar_multiplier_max": 0.35,
            "temp_mean": 22.0,
            "temp_std": 1.5,
            "irradiance_multiplier_min": 0.15,
            "irradiance_multiplier_max": 0.35,
        },
    })

    # Demand Uncertainty Distribution
    demand_mean_multiplier: float = 1.0
    demand_std_multiplier: float = 0.08
    demand_min_multiplier: float = 0.70
    demand_max_multiplier: float = 1.35
    demand_temporal_correlation: float = 0.65  # AR(1) autocorrelation across consecutive hours

    # Time-of-Use Electricity Tariff Assumptions (INR/kWh)
    price_schedules: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "Off-Peak": {
            "hours": [22, 23, 0, 1, 2, 3, 4, 5],
            "day_ahead_inr_kwh": 4.20,
            "real_time_markup_std": 0.45,
            "description": "Late night & early morning utility off-peak window",
        },
        "Normal": {
            "hours": [6, 7, 8, 9, 10, 11, 12, 13, 20, 21],
            "day_ahead_inr_kwh": 7.50,
            "real_time_markup_std": 0.65,
            "description": "Standard business and academic operating daytime window",
        },
        "Peak": {
            "hours": [14, 15, 16, 17, 18, 19],
            "day_ahead_inr_kwh": 11.80,
            "real_time_markup_std": 1.20,
            "description": "Evening grid peak period with highest commercial tariff",
        },
    })


DEFAULT_SCENARIO_PARAMS = ScenarioParameters()

