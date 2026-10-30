"""
GRIDWISE AI - Unit Tests for Campus Demand Dataset
"""

import pytest
import pandas as pd
from pathlib import Path
from services.demand_generator import CampusDemandGenerator

BASE_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def demand_df():
    """Load or generate demand dataframe."""
    csv_path = BASE_DIR / "data" / "processed" / "campus_demand_hourly.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    gen = CampusDemandGenerator(seed=42)
    return gen.generate()


def test_demand_record_count(demand_df):
    """Verify exactly 8760 hourly records (365 days * 24 hours)."""
    assert len(demand_df) == 8760


def test_demand_columns(demand_df):
    """Verify required demand columns are present."""
    required = [
        "timestamp",
        "date",
        "hour",
        "day_type",
        "base_demand_kwh",
        "actual_demand_kwh",
        "demand_uncertainty",
    ]
    for col in required:
        assert col in demand_df.columns


def test_demand_non_negative(demand_df):
    """Verify that demand is strictly non-negative."""
    assert (demand_df["actual_demand_kwh"] >= 0).all()
    assert (demand_df["base_demand_kwh"] >= 0).all()


def test_demand_weekday_vs_weekend(demand_df):
    """Verify weekday demand average is higher than weekend demand average."""
    weekday_mean = demand_df[demand_df["day_type"] == "Weekday"]["actual_demand_kwh"].mean()
    weekend_mean = demand_df[demand_df["day_type"] == "Weekend"]["actual_demand_kwh"].mean()
    assert weekday_mean > weekend_mean
    assert weekend_mean > 150.0  # Base facilities still active on weekends


def test_demand_no_duplicate_or_missing_timestamps(demand_df):
    """Verify timestamp continuity and uniqueness."""
    assert demand_df["timestamp"].isna().sum() == 0
    assert demand_df["timestamp"].duplicated().sum() == 0

