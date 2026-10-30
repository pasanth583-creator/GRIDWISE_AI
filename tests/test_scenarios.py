"""
GRIDWISE AI - Unit Tests for Stochastic Scenarios
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from services.weather_generator import WeatherScenarioGenerator
from services.scenario_generator import CombinedScenarioGenerator

BASE_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def weather_scenarios_df():
    csv_path = BASE_DIR / "data" / "scenarios" / "weather_scenarios_500.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    gen = WeatherScenarioGenerator()
    return gen.generate()


@pytest.fixture
def combined_scenarios_df():
    csv_path = BASE_DIR / "data" / "scenarios" / "combined_scenarios_500.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    gen = CombinedScenarioGenerator()
    return gen.generate_combined_scenarios()


def test_weather_scenario_count(weather_scenarios_df):
    """Verify exactly 500 weather scenarios exist."""
    assert len(weather_scenarios_df) == 500


def test_weather_probabilities_sum_to_one(weather_scenarios_df):
    """Verify scenario probabilities sum to 1.0."""
    total_prob = weather_scenarios_df["probability"].sum()
    assert np.isclose(total_prob, 1.0, atol=1e-5)


def test_weather_categories_present(weather_scenarios_df):
    """Verify all 4 required weather conditions are represented."""
    conditions = set(weather_scenarios_df["weather_condition"].unique())
    expected = {"Sunny", "Partly Cloudy", "Cloudy", "Rainy"}
    assert conditions == expected


def test_combined_scenarios_record_count(combined_scenarios_df):
    """Verify 500 scenarios * 24 hours = 12,000 total observations."""
    assert len(combined_scenarios_df) == 12000


def test_combined_scenario_hours_per_scenario(combined_scenarios_df):
    """Verify every scenario has exactly 24 hourly records."""
    counts = combined_scenarios_df.groupby("scenario_id")["hour"].count()
    assert len(counts) == 500
    assert (counts == 24).all()


def test_combined_scenarios_no_nulls(combined_scenarios_df):
    """Verify zero missing values in combined scenario dataset."""
    assert combined_scenarios_df.isna().sum().sum() == 0


def test_combined_scenario_probabilities_sum_to_one(combined_scenarios_df):
    """Verify total probability across 500 distinct scenarios sums to 1.0."""
    scenario_probs = combined_scenarios_df.groupby("scenario_id")["probability"].first()
    assert np.isclose(scenario_probs.sum(), 1.0, atol=1e-5)

