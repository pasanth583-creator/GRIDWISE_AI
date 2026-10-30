"""
GRIDWISE AI - Unit Tests for Electricity Price Dataset
"""

import pytest
import pandas as pd
from pathlib import Path
from services.price_generator import ElectricityPriceGenerator

BASE_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def price_df():
    """Load or generate price dataframe."""
    csv_path = BASE_DIR / "data" / "processed" / "electricity_prices_hourly.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    gen = ElectricityPriceGenerator(seed=42)
    return gen.generate()


def test_price_record_count(price_df):
    """Verify exactly 8760 records."""
    assert len(price_df) == 8760


def test_price_columns(price_df):
    """Verify required price columns exist."""
    required = [
        "timestamp",
        "hour",
        "day_ahead_price_inr_kwh",
        "real_time_price_inr_kwh",
        "price_category",
    ]
    for col in required:
        assert col in price_df.columns


def test_prices_strictly_positive(price_df):
    """Verify all day-ahead and real-time electricity prices are strictly positive."""
    assert (price_df["day_ahead_price_inr_kwh"] > 0).all()
    assert (price_df["real_time_price_inr_kwh"] > 0).all()


def test_price_tier_hierarchy(price_df):
    """Verify that Peak prices > Normal prices > Off-Peak prices on average."""
    off_peak_mean = price_df[price_df["price_category"] == "Off-Peak"]["day_ahead_price_inr_kwh"].mean()
    normal_mean = price_df[price_df["price_category"] == "Normal"]["day_ahead_price_inr_kwh"].mean()
    peak_mean = price_df[price_df["price_category"] == "Peak"]["day_ahead_price_inr_kwh"].mean()

    assert peak_mean > normal_mean
    assert normal_mean > off_peak_mean

