"""
GRIDWISE AI - Weather Scenario Generator
Generates 500 reproducible discrete weather scenarios with exact probability weighting.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from config.scenario_parameters import DEFAULT_SCENARIO_PARAMS, ScenarioParameters


class WeatherScenarioGenerator:
    """
    Synthesizes 500 reproducible weather scenarios for stochastic programming.

    Categories:
    - Sunny (35% probability): Low cloud cover, high irradiance multiplier (1.05 - 1.25).
    - Partly Cloudy (30% probability): Medium cloud cover, moderate solar yield (0.75 - 1.00).
    - Cloudy (20% probability): Heavy cloud cover, suppressed solar yield (0.40 - 0.70).
    - Rainy (15% probability): Overcast skies, precipitation attenuation (0.15 - 0.35).

    Total probabilities sum strictly to 1.0000.
    """

    def __init__(self, params: Optional[ScenarioParameters] = None):
        self.params = params or DEFAULT_SCENARIO_PARAMS
        self.rng = np.random.default_rng(self.params.random_seed)

    def generate(self) -> pd.DataFrame:
        """
        Generates 500 weather scenarios with normalized probabilities.
        """
        n_scenarios = self.params.num_scenarios
        conditions = list(self.params.weather_probabilities.keys())
        cat_probs = [self.params.weather_probabilities[c] for c in conditions]

        # Allocate scenario counts proportionally to ensure sample representation
        counts = [int(round(p * n_scenarios)) for p in cat_probs]
        diff = n_scenarios - sum(counts)
        counts[0] += diff  # Adjust any rounding discrepancy on Sunny

        records = []
        scenario_idx = 1
        
        # Base equal probability for each of the 500 scenarios = 1 / 500 = 0.002
        individual_prob = 1.0 / n_scenarios

        for cond, count in zip(conditions, counts):
            prof = self.params.weather_profiles[cond]
            for _ in range(count):
                cloud_cover = self.rng.uniform(prof["cloud_cover_min"], prof["cloud_cover_max"])
                solar_mult = self.rng.uniform(prof["solar_multiplier_min"], prof["solar_multiplier_max"])
                irr_mult = self.rng.uniform(prof["irradiance_multiplier_min"], prof["irradiance_multiplier_max"])
                temp_c = self.rng.normal(prof["temp_mean"], prof["temp_std"])

                records.append({
                    "scenario_id": f"SCEN_{scenario_idx:04d}",
                    "weather_condition": cond,
                    "probability": round(float(individual_prob), 6),
                    "cloud_cover": round(float(cloud_cover), 3),
                    "solar_multiplier": round(float(solar_mult), 3),
                    "temperature_c": round(float(temp_c), 1),
                    "irradiance_multiplier": round(float(irr_mult), 3),
                })
                scenario_idx += 1

        df = pd.DataFrame(records)
        
        # Ensure exact probability summation to 1.000000
        prob_sum = df["probability"].sum()
        df["probability"] = df["probability"] / prob_sum

        return df


def generate_weather_scenarios(output_path: Optional[str] = None) -> pd.DataFrame:
    """Helper to generate and save weather scenarios."""
    gen = WeatherScenarioGenerator()
    df = gen.generate()
    if output_path:
        df.to_csv(output_path, index=False)
    return df

