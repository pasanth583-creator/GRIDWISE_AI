"""
GRIDWISE AI - Electricity Price Dataset Generator
Generates 365 days of realistic simulated Time-of-Use (TOU) electricity tariffs (8760 records).
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional


class ElectricityPriceGenerator:
    """
    Synthesizes 8760-hour Time-of-Use (TOU) electricity market pricing.

    Tariff Architecture (Simulated Commercial / Institutional Indian Grid Tariff):
    - Off-Peak Window (22:00 - 05:00):
        Base Day-Ahead: ~4.20 INR/kWh.
        Encourages nocturnal battery charging and load shifting.
    - Normal / Daytime Operating Window (06:00 - 13:00, 20:00 - 21:00):
        Base Day-Ahead: ~7.50 INR/kWh.
        Reflects regular daytime grid dispatch and commercial demand.
    - Peak Window (14:00 - 19:00):
        Base Day-Ahead: ~11.80 INR/kWh.
        Represents regional grid peak strain, solar decline, and high air conditioning load.
    
    Real-Time Balancing Price:
        Models real-time spot energy procurement fluctuations.
        During peak hours, occasional stochastic price surges occur reflecting power exchange volatility.
        All prices remain strictly positive (> 0.0 INR/kWh).
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def _get_price_category(self, hour: int) -> str:
        """Categorize hour into Off-Peak, Normal, or Peak."""
        if hour in [22, 23, 0, 1, 2, 3, 4, 5]:
            return "Off-Peak"
        elif hour in [14, 15, 16, 17, 18, 19]:
            return "Peak"
        else:
            return "Normal"

    def generate(self, start_date: str = "2026-01-01") -> pd.DataFrame:
        """
        Generates 8760 hourly electricity price records.
        """
        timestamps = pd.date_range(start=start_date, periods=8760, freq="h")
        records = []

        for ts in timestamps:
            hour = ts.hour
            day_of_year = ts.dayofyear
            category = self._get_price_category(hour)

            # Seasonal market price fluctuation (summer spot prices slightly elevated)
            season_mult = 1.0 + 0.08 * np.sin(2 * np.pi * (day_of_year - 50) / 365)

            if category == "Off-Peak":
                da_base = 4.20 * season_mult
                # Mild real-time noise around DA price
                rt_noise = self.rng.normal(0.0, 0.35)
                rt_price = max(2.50, da_base + rt_noise)
            elif category == "Normal":
                da_base = 7.50 * season_mult
                rt_noise = self.rng.normal(0.0, 0.65)
                rt_price = max(4.50, da_base + rt_noise)
            else:  # Peak
                da_base = 11.80 * season_mult
                # During peak, 12% probability of real-time spot price surge
                if self.rng.random() < 0.12:
                    spike_markup = self.rng.uniform(2.50, 6.00)
                else:
                    spike_markup = self.rng.normal(0.20, 0.90)
                rt_price = max(8.00, da_base + spike_markup)

            records.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "date": ts.strftime("%Y-%m-%d"),
                "hour": hour,
                "day_ahead_price_inr_kwh": round(float(da_base), 3),
                "real_time_price_inr_kwh": round(float(rt_price), 3),
                "price_category": category,
            })

        df = pd.DataFrame(records)
        return df


def generate_price_dataset(output_path: Optional[str] = None) -> pd.DataFrame:
    """Helper to generate and save electricity price dataset."""
    gen = ElectricityPriceGenerator(seed=42)
    df = gen.generate()
    if output_path:
        df.to_csv(output_path, index=False)
    return df

