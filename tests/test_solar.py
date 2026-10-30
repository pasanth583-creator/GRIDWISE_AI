"""
GRIDWISE AI - Unit Tests for Solar PV Generation Dataset
"""

import pytest
import pandas as pd
from pathlib import Path
from services.solar_generator import SolarGenerationGenerator

BASE_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def solar_df():
    """Load or generate solar dataframe."""
    csv_path = BASE_DIR / "data" / "processed" / "solar_generation_hourly.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    gen = SolarGenerationGenerator(solar_capacity_kwp=800.0, seed=42)
    return gen.generate()


def test_solar_record_count(solar_df):
    """Verify exactly 8760 records."""
    assert len(solar_df) == 8760


def test_solar_columns(solar_df):
    """Verify required columns exist."""
    required = [
        "timestamp",
        "date",
        "hour",
        "solar_capacity_kwp",
        "irradiance_wm2",
        "cloud_cover",
        "temperature_c",
        "weather_condition",
        "solar_generation_kwh",
    ]
    for col in required:
        assert col in solar_df.columns


def test_solar_zero_at_night(solar_df):
    """Verify strictly 0 generation during nocturnal hours."""
    night_hours = [20, 21, 22, 23, 0, 1, 2, 3, 4, 5]
    night_gen = solar_df[solar_df["hour"].isin(night_hours)]["solar_generation_kwh"]
    assert (night_gen == 0.0).all()


def test_solar_does_not_exceed_capacity(solar_df):
    """Verify solar generation never exceeds installed 800 kWp nameplate capacity."""
    max_gen = solar_df["solar_generation_kwh"].max()
    assert max_gen <= 800.0
    assert max_gen > 400.0  # Must generate meaningful peak power


def test_solar_weather_condition_effects(solar_df):
    """Verify sunny conditions produce higher average solar yield than rainy conditions."""
    daylight = solar_df[solar_df["hour"].between(9, 15)]
    sunny_mean = daylight[daylight["weather_condition"] == "Sunny"]["solar_generation_kwh"].mean()
    rainy_mean = daylight[daylight["weather_condition"] == "Rainy"]["solar_generation_kwh"].mean()
    assert sunny_mean > rainy_mean
    assert rainy_mean > 0  # Some diffuse light still present during rain

