"""
GRIDWISE AI - Combined Stochastic Scenario Generator
Synthesizes 500 combined weather-demand-price scenarios with 24-hour horizon (12,000 records).
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
from config.scenario_parameters import DEFAULT_SCENARIO_PARAMS, ScenarioParameters
from config.energy_parameters import DEFAULT_ENERGY_PARAMS, EnergyParameters
from services.weather_generator import WeatherScenarioGenerator


class CombinedScenarioGenerator:
    """
    Generates 500 combined stochastic scenarios for day-ahead microgrid procurement.

    Mathematical Properties:
    - 500 distinct scenarios with 24 hourly steps each (12,000 observations total).
    - Scenario probability: Each scenario has weight pi_s = 0.002, with sum(pi_s) = 1.0000.
    - Demand uncertainty: Correlated AR(1) process with daily variance shift.
        multiplier(t) = mu + rho * (multiplier(t-1) - mu) + sqrt(1 - rho^2) * eps(t)
        Preserves physical thermal and operational load inertia across campus buildings.
    - Solar generation: Coupled with discrete weather scenario multipliers and diurnal solar curve.
    - Prices: Time-of-Use structure with stochastic real-time balancing markups.
    """

    def __init__(
        self,
        scenario_params: Optional[ScenarioParameters] = None,
        energy_params: Optional[EnergyParameters] = None,
    ):
        self.scenario_params = scenario_params or DEFAULT_SCENARIO_PARAMS
        self.energy_params = energy_params or DEFAULT_ENERGY_PARAMS
        self.rng = np.random.default_rng(self.scenario_params.random_seed + 101)

    def _get_base_24h_demand(self) -> np.ndarray:
        """Standard weekday 24-hour baseline campus demand profile (kW)."""
        return np.array([
            230, 215, 210, 205, 215, 260,
            360, 520, 720, 840, 890, 915,
            870, 860, 910, 925, 880, 740,
            620, 540, 460, 390, 310, 260
        ], dtype=float)

    def _get_base_24h_clear_sky_solar(self) -> np.ndarray:
        """Standard 24-hour clear-sky solar generation profile for 800 kWp array (kW)."""
        # Astronomical curve peaking at solar noon (~680-720 kW AC after losses)
        profile = np.zeros(24, dtype=float)
        # Solar active hours: 06:00 to 18:00
        active_hours = np.arange(6, 19)
        # Sine half-wave over 12 daylight hours
        angles = np.pi * (active_hours - 6) / 12.0
        peak_power = self.energy_params.solar_installed_capacity_kwp * 0.90  # 720 kW AC peak
        profile[active_hours] = peak_power * np.sin(angles)
        return profile

    def _get_base_24h_prices(self) -> Tuple[np.ndarray, np.ndarray]:
        """Returns baseline day-ahead and real-time prices for 24 hours (INR/kWh)."""
        da_prices = np.zeros(24, dtype=float)
        rt_prices = np.zeros(24, dtype=float)

        for h in range(24):
            if h in [22, 23, 0, 1, 2, 3, 4, 5]:
                da_prices[h] = 4.20
                rt_prices[h] = 4.20 + self.rng.normal(0, 0.3)
            elif h in [14, 15, 16, 17, 18, 19]:
                da_prices[h] = 11.80
                rt_prices[h] = 11.80 + self.rng.normal(0.4, 0.8)
            else:
                da_prices[h] = 7.50
                rt_prices[h] = 7.50 + self.rng.normal(0.1, 0.5)

        rt_prices = np.maximum(2.0, rt_prices)
        return da_prices, rt_prices

    def generate_demand_scenarios(self) -> pd.DataFrame:
        """
        Generates 500 demand uncertainty scenarios (500 * 24 = 12,000 records).
        """
        n_scenarios = self.scenario_params.num_scenarios
        base_demand = self._get_base_24h_demand()
        rho = self.scenario_params.demand_temporal_correlation

        records = []
        for s_idx in range(1, n_scenarios + 1):
            scen_id = f"SCEN_{s_idx:04d}"
            
            # Daily macro shift (e.g. hotter day or high activity campus event)
            macro_shift = self.rng.normal(1.0, 0.05)
            
            # Hour-to-hour AR(1) process
            multiplier = macro_shift
            for h in range(24):
                white_noise = self.rng.normal(0.0, self.scenario_params.demand_std_multiplier)
                multiplier = 1.0 + rho * (multiplier - 1.0) + np.sqrt(1 - rho**2) * white_noise
                multiplier = max(
                    self.scenario_params.demand_min_multiplier,
                    min(self.scenario_params.demand_max_multiplier, multiplier)
                )

                scen_demand = max(100.0, base_demand[h] * multiplier)

                records.append({
                    "scenario_id": scen_id,
                    "hour": h,
                    "demand_multiplier": round(float(multiplier), 4),
                    "scenario_demand_kwh": round(float(scen_demand), 2),
                })

        return pd.DataFrame(records)

    def generate_combined_scenarios(self) -> pd.DataFrame:
        """
        Generates 500 combined scenarios containing:
        scenario_id, hour, weather_condition, probability, demand_kwh,
        solar_kwh, day_ahead_price_inr_kwh, real_time_price_inr_kwh.
        Total records: 500 * 24 = 12,000.
        """
        # 1. Generate 500 weather macro-scenarios
        weather_gen = WeatherScenarioGenerator(self.scenario_params)
        df_weather = weather_gen.generate()

        # 2. Generate 500 demand scenarios
        df_demand = self.generate_demand_scenarios()

        # Baseline 24-hr curves
        base_solar = self._get_base_24h_clear_sky_solar()
        base_da_prices, base_rt_prices = self._get_base_24h_prices()

        records = []
        weather_map = df_weather.set_index("scenario_id").to_dict(orient="index")

        demand_grouped = df_demand.groupby("scenario_id")

        for scen_id, demand_group in demand_grouped:
            w_info = weather_map[scen_id]
            w_cond = w_info["weather_condition"]
            w_prob = w_info["probability"]
            solar_mult = w_info["solar_multiplier"]

            demand_vals = demand_group.sort_values("hour")["scenario_demand_kwh"].values

            # Correlated solar noise for this scenario
            hourly_solar_noise = self.rng.normal(1.0, 0.04, size=24)

            for h in range(24):
                # Calculate hourly solar under this scenario
                if h < 6 or h >= 19:
                    solar_output = 0.0
                else:
                    raw_solar = base_solar[h] * solar_mult * hourly_solar_noise[h]
                    solar_output = min(
                        self.energy_params.solar_installed_capacity_kwp,
                        max(0.0, raw_solar)
                    )

                # Real-time price stochastic noise for this scenario
                rt_noise = self.rng.normal(0.0, 0.4)
                if w_cond in ["Rainy", "Cloudy"] and h in [14, 15, 16, 17, 18, 19]:
                    # Severe weather peak price pressure
                    rt_price = base_rt_prices[h] + self.rng.uniform(0.5, 1.8)
                else:
                    rt_price = max(2.50, base_rt_prices[h] + rt_noise)

                records.append({
                    "scenario_id": scen_id,
                    "hour": h,
                    "weather_condition": w_cond,
                    "probability": round(float(w_prob), 6),
                    "demand_kwh": round(float(demand_vals[h]), 2),
                    "solar_kwh": round(float(solar_output), 2),
                    "day_ahead_price_inr_kwh": round(float(base_da_prices[h]), 3),
                    "real_time_price_inr_kwh": round(float(rt_price), 3),
                })

        df_combined = pd.DataFrame(records)
        return df_combined


def generate_all_scenarios(
    scenarios_path: Optional[str] = None,
    demand_scenarios_path: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Helper to generate and save combined scenario files."""
    gen = CombinedScenarioGenerator()
    df_demand_scen = gen.generate_demand_scenarios()
    df_combined = gen.generate_combined_scenarios()

    if demand_scenarios_path:
        df_demand_scen.to_csv(demand_scenarios_path, index=False)
    if scenarios_path:
        df_combined.to_csv(scenarios_path, index=False)

    return df_demand_scen, df_combined

