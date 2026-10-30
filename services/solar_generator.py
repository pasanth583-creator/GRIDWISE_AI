"""
GRIDWISE AI - Solar Generation Dataset Generator
Generates 365 days of realistic hourly solar production (8760 records).
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple


class SolarGenerationGenerator:
    """
    Synthesizes 8760-hour solar PV production for an 800 kWp campus array.

    Models:
    - Solar geometry: Hour angle, solar declination, zenith angle, and air mass.
    - Clear-sky Global Horizontal Irradiance (GHI) based on modified Haurwitz/Adnot model.
    - Weather conditions: Sunny, Partly Cloudy, Cloudy, Rainy.
    - Cloud attenuation factor reducing direct and diffuse components.
    - Ambient temperature and photovoltaic cell temperature derating:
        T_cell = T_amb + ((NOCT - 20) / 800) * GHI
        P_dc = P_capacity * (GHI / 1000) * (1 - gamma * (T_cell - 25))
        P_ac = min(P_capacity, P_dc * eta_inverter)
    - Zero generation strictly enforced during nocturnal hours (zenith >= 90° or GHI <= 0).
    """

    def __init__(
        self,
        solar_capacity_kwp: float = 800.0,
        latitude_deg: float = 13.08,  # Tropical / Chennai / Bangalore latitude
        gamma_temp_coeff: float = 0.0035,  # -0.35% per °C above 25°C
        noct_deg_c: float = 45.0,
        inverter_efficiency: float = 0.975,
        seed: int = 42,
    ):
        self.capacity = solar_capacity_kwp
        self.latitude = np.radians(latitude_deg)
        self.gamma = gamma_temp_coeff
        self.noct = noct_deg_c
        self.eta_inv = inverter_efficiency
        self.rng = np.random.default_rng(seed)

    def _calculate_clear_sky_ghi(self, day_of_year: int, hour: int) -> Tuple[float, float]:
        """
        Calculates solar elevation angle and clear-sky GHI (W/m²).
        Returns (ghi_clear_sky, elevation_angle_deg).
        """
        # Solar declination angle delta
        delta = np.radians(23.45 * np.sin(np.radians(360 / 365 * (284 + day_of_year))))
        
        # Solar hour angle omega (solar noon at 12:00)
        omega = np.radians(15 * (hour - 12))

        # Solar elevation angle alpha
        sin_alpha = np.sin(self.latitude) * np.sin(delta) + np.cos(self.latitude) * np.cos(delta) * np.cos(omega)
        
        # Sun is below horizon
        if sin_alpha <= 0.0:
            return 0.0, 0.0

        elevation_deg = np.degrees(np.arcsin(sin_alpha))
        zenith_deg = 90.0 - elevation_deg

        # Clear-sky extraterrestrial irradiance modulated by day of year eccentricity
        e0 = 1.0 + 0.033 * np.cos(np.radians(360 * day_of_year / 365))
        i_sc = 1367.0 * e0  # Solar constant

        # Standard atmospheric transmission function
        air_mass = 1.0 / (np.sin(np.radians(elevation_deg)) + 0.001)
        transmittance = 0.7 ** (air_mass ** 0.678)
        ghi = i_sc * np.sin(np.radians(elevation_deg)) * transmittance

        # Physical bounds
        ghi = max(0.0, min(1150.0, ghi))
        return ghi, elevation_deg

    def _determine_weather_condition(self, day_of_year: int) -> Tuple[str, float, float]:
        """
        Assigns weather condition, cloud cover (0.0 to 1.0), and daily temp base.
        Incorporates realistic monsoon seasonality (Jul-Sep higher rain/cloud).
        """
        is_monsoon = (182 <= day_of_year <= 273)  # July to September
        
        if is_monsoon:
            probs = [0.15, 0.30, 0.35, 0.20]  # Sunny, Partly Cloudy, Cloudy, Rainy
        else:
            probs = [0.45, 0.32, 0.15, 0.08]

        condition = self.rng.choice(
            ["Sunny", "Partly Cloudy", "Cloudy", "Rainy"],
            p=probs,
        )

        if condition == "Sunny":
            cloud_cover = self.rng.uniform(0.03, 0.20)
            temp_base = 31.0 + 3.0 * np.sin(2 * np.pi * (day_of_year - 60) / 365)
        elif condition == "Partly Cloudy":
            cloud_cover = self.rng.uniform(0.22, 0.50)
            temp_base = 28.5 + 2.5 * np.sin(2 * np.pi * (day_of_year - 60) / 365)
        elif condition == "Cloudy":
            cloud_cover = self.rng.uniform(0.55, 0.82)
            temp_base = 25.0 + 2.0 * np.sin(2 * np.pi * (day_of_year - 60) / 365)
        else:  # Rainy
            cloud_cover = self.rng.uniform(0.85, 0.98)
            temp_base = 22.5 + 1.5 * np.sin(2 * np.pi * (day_of_year - 60) / 365)

        return condition, cloud_cover, temp_base

    def generate(self, start_date: str = "2026-01-01") -> pd.DataFrame:
        """
        Generates 8760 hourly solar production records.
        """
        timestamps = pd.date_range(start=start_date, periods=8760, freq="h")
        records = []

        current_day = -1
        current_condition = "Sunny"
        current_cloud_cover = 0.1
        current_temp_base = 30.0

        for ts in timestamps:
            day_of_year = ts.dayofyear
            hour = ts.hour

            # Update daily macro weather profile at start of each day
            if day_of_year != current_day:
                current_day = day_of_year
                current_condition, current_cloud_cover, current_temp_base = self._determine_weather_condition(day_of_year)

            # Intra-day cloud fluctuations
            hourly_cloud_variation = np.clip(
                current_cloud_cover + self.rng.normal(0.0, 0.05), 0.0, 1.0
            )

            # Astronomical clear-sky GHI
            clear_ghi, elevation = self._calculate_clear_sky_ghi(day_of_year, hour)

            # Nocturnal filter: Strict 0 generation
            if elevation <= 0.0 or clear_ghi <= 0.0 or hour < 6 or hour >= 19:
                ghi_actual = 0.0
                solar_gen_kwh = 0.0
                ambient_temp = current_temp_base - 4.0 + 1.0 * np.cos(np.radians(15 * (hour - 3)))
            else:
                # Cloud attenuation: diffuse and beam fraction scaling
                cloud_transmission = (1.0 - 0.78 * (hourly_cloud_variation ** 1.4))
                ghi_actual = clear_ghi * cloud_transmission

                # Diurnal temperature cycle: peak around 14:00
                diurnal_temp_shift = 5.5 * np.sin(np.radians(15 * (hour - 8)))
                ambient_temp = current_temp_base + diurnal_temp_shift + self.rng.normal(0, 0.5)

                # PV cell temperature model
                t_cell = ambient_temp + ((self.noct - 20.0) / 800.0) * ghi_actual

                # Temperature derating
                temp_derating = 1.0 - self.gamma * (t_cell - 25.0)
                temp_derating = max(0.70, min(1.05, temp_derating))

                # DC power generation
                p_dc = self.capacity * (ghi_actual / 1000.0) * temp_derating
                
                # AC power with inverter efficiency, strictly capped at nameplate capacity
                p_ac = min(self.capacity, p_dc * self.eta_inv)
                solar_gen_kwh = max(0.0, p_ac)

            records.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "date": ts.strftime("%Y-%m-%d"),
                "hour": hour,
                "solar_capacity_kwp": self.capacity,
                "irradiance_wm2": round(float(ghi_actual), 2),
                "cloud_cover": round(float(hourly_cloud_variation), 3),
                "temperature_c": round(float(ambient_temp), 1),
                "weather_condition": current_condition,
                "solar_generation_kwh": round(float(solar_gen_kwh), 2),
            })

        df = pd.DataFrame(records)
        return df


def generate_solar_dataset(output_path: Optional[str] = None, capacity_kwp: float = 800.0) -> pd.DataFrame:
    """Helper to generate and save solar generation dataset."""
    gen = SolarGenerationGenerator(solar_capacity_kwp=capacity_kwp, seed=42)
    df = gen.generate()
    if output_path:
        df.to_csv(output_path, index=False)
    return df

