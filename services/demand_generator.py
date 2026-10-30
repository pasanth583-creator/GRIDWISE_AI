"""
GRIDWISE AI - Campus Electricity Demand Dataset Generator
Generates 365 days of realistic hourly campus demand (8760 records).
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


class CampusDemandGenerator:
    """
    Synthesizes realistic 8760-hour campus electrical demand.

    Models:
    - Base nocturnal load: Essential facilities, data centers, cold storage, security (180 - 240 kW).
    - Morning ramp-up: Classrooms opening, cafeteria prep, administrative staff arrival (06:00 - 09:00).
    - Academic core peak: Lectures, laboratories, high-performance computing, HVAC chillers (09:00 - 17:00).
    - Evening transition: Libraries, dining halls, student hostels, study areas (17:00 - 22:00).
    - Weekday vs. Weekend operational divergence (Weekends operate at 50-60% of weekday peak).
    - Seasonal calendar shifts: Summer term / semester exams (high thermal cooling) vs. vacation recess.
    """

    def __init__(self, seed: int = 42, start_year: int = 2026):
        self.seed = seed
        self.start_year = start_year
        self.rng = np.random.default_rng(seed)

    def _get_hourly_diurnal_profile(self, hour: int, is_weekend: bool) -> float:
        """Returns baseline diurnal demand shape (in kW) as a function of hour and day type."""
        if not is_weekend:
            # Weekday profile (Mon - Fri)
            # 00:00 - 05:00: Night base load (~220 kW)
            # 06:00 - 08:00: Morning ramp (300 -> 580 kW)
            # 09:00 - 13:00: Academic morning peak (750 -> 880 kW)
            # 14:00 - 17:00: Afternoon peak + chillers (850 -> 920 kW)
            # 18:00 - 21:00: Evening library & hostel load (550 -> 420 kW)
            # 22:00 - 23:00: Night tapering (320 -> 240 kW)
            hourly_weights = [
                230, 215, 210, 205, 215, 260,  # 00 - 05
                360, 520, 720, 840, 890, 915,  # 06 - 11
                870, 860, 910, 925, 880, 740,  # 12 - 17
                620, 540, 460, 390, 310, 260   # 18 - 23
            ]
        else:
            # Weekend profile (Sat - Sun): reduced academic buildings, persistent hostel/library
            hourly_weights = [
                190, 180, 175, 175, 180, 210,  # 00 - 05
                260, 320, 390, 440, 480, 510,  # 06 - 11
                490, 470, 480, 490, 460, 410,  # 12 - 17
                380, 360, 330, 290, 240, 210   # 18 - 23
            ]
        return float(hourly_weights[hour])

    def _get_seasonal_multiplier(self, day_of_year: int) -> float:
        """
        Seasonal factor: Summer heatwave/HVAC peak (Apr-Jun in India / tropical),
        Monsoon moderate (Jul-Sep), Autumn/Winter comfortable (Oct-Feb).
        """
        # Sine cycle peaking around day 135 (mid-May summer)
        summer_factor = 1.0 + 0.16 * np.sin(2 * np.pi * (day_of_year - 45) / 365)
        
        # Campus academic calendar dip during summer vacation (June, days 152 to 181)
        if 152 <= day_of_year <= 181:
            summer_factor *= 0.82
        # Winter break dip (late Dec, days 355 to 365)
        elif day_of_year >= 355:
            summer_factor *= 0.85

        return float(summer_factor)

    def generate(self, start_date: str = "2026-01-01") -> pd.DataFrame:
        """
        Generates 8760 hourly campus electricity demand records.
        """
        timestamps = pd.date_range(start=start_date, periods=8760, freq="h")
        records = []

        # Auto-regressive uncertainty process to ensure realistic temporal smoothness
        ar_noise = 0.0
        ar_coeff = 0.70  # AR(1) parameter

        for ts in timestamps:
            hour = ts.hour
            day_of_year = ts.dayofyear
            is_weekend = (ts.weekday() >= 5)
            day_type = "Weekend" if is_weekend else "Weekday"

            base_diurnal = self._get_hourly_diurnal_profile(hour, is_weekend)
            seasonal_mult = self._get_seasonal_multiplier(day_of_year)
            base_demand = base_diurnal * seasonal_mult

            # AR(1) Gaussian noise (mean 0, std ~ 25 kW)
            white_noise = self.rng.normal(loc=0.0, scale=20.0)
            ar_noise = ar_coeff * ar_noise + np.sqrt(1 - ar_coeff**2) * white_noise

            # Bounded actual demand
            actual_demand = max(120.0, base_demand + ar_noise)
            demand_uncertainty = actual_demand - base_demand

            records.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "date": ts.strftime("%Y-%m-%d"),
                "hour": hour,
                "day_type": day_type,
                "base_demand_kwh": round(float(base_demand), 2),
                "actual_demand_kwh": round(float(actual_demand), 2),
                "demand_uncertainty": round(float(demand_uncertainty), 2),
            })

        df = pd.DataFrame(records)
        return df


def generate_demand_dataset(output_path: Optional[str] = None) -> pd.DataFrame:
    """Helper to generate and save campus demand dataset."""
    gen = CampusDemandGenerator(seed=42)
    df = gen.generate()
    if output_path:
        df.to_csv(output_path, index=False)
    return df

