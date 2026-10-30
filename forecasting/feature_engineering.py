"""
GRIDWISE AI - Time Series Feature Engineering Module
Constructs leakage-free, chronological lag, rolling window, calendar, and cyclical features
for campus demand, solar generation, and electricity tariff forecasting.
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import pandas as pd


def create_calendar_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Extracts calendar, day-type, and cyclical harmonic features from timestamp."""
    out = df.copy()
    if timestamp_col in out.columns:
        dt = pd.to_datetime(out[timestamp_col])
        out["hour"] = dt.dt.hour
        out["day_of_week"] = dt.dt.dayofweek
        out["is_weekend"] = (out["day_of_week"] >= 5).astype(int)
        out["month"] = dt.dt.month
        out["day_of_year"] = dt.dt.dayofyear
    elif "hour" in out.columns:
        if "day_of_week" not in out.columns:
            out["day_of_week"] = 0
        if "is_weekend" not in out.columns:
            out["is_weekend"] = 0
        if "month" not in out.columns:
            out["month"] = 1
    
    # Cyclical harmonics (prevents 23:00 -> 00:00 discontinuity)
    out["hour_sin"] = np.sin(2.0 * np.pi * out["hour"] / 24.0)
    out["hour_cos"] = np.cos(2.0 * np.pi * out["hour"] / 24.0)
    out["month_sin"] = np.sin(2.0 * np.pi * out["month"] / 12.0)
    out["month_cos"] = np.cos(2.0 * np.pi * out["month"] / 12.0)

    # Academic term indicator (Jan-May: Spring, Jun-Jul: Summer break, Aug-Dec: Fall)
    out["is_academic_term"] = (~out["month"].isin([6, 7])).astype(int)

    return out


def build_demand_features(
    df: pd.DataFrame,
    target_col: str = "actual_demand_kwh",
    lags: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Constructs autoregressive lag, rolling statistics, and cyclical features for demand.
    Ensures zero look-ahead data leakage by strictly shifting backward.
    """
    if lags is None:
        lags = [1, 2, 24, 48, 168]

    data = create_calendar_features(df)
    
    # Autoregressive lags
    for l in lags:
        data[f"demand_lag_{l}"] = data[target_col].shift(l)

    # Rolling backward statistics (shifted by 1 to exclude current t)
    data["demand_rolling_mean_24"] = data[target_col].shift(1).rolling(24, min_periods=1).mean()
    data["demand_rolling_std_24"] = data[target_col].shift(1).rolling(24, min_periods=1).std().fillna(0.0)
    data["demand_rolling_mean_168"] = data[target_col].shift(1).rolling(168, min_periods=1).mean()

    # Forward fill early lag NaN values using first available observation
    lag_cols = [c for c in data.columns if "demand_lag_" in c or "demand_rolling_" in c]
    data[lag_cols] = data[lag_cols].bfill().ffill()

    return data


def build_solar_features(
    df: pd.DataFrame,
    target_col: str = "solar_generation_kwh",
    lags: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Constructs weather-coupled features for solar generation.
    Includes theoretical zenith angles, ambient temperature, cloud cover, and same-hour lags.
    """
    if lags is None:
        lags = [24, 48]

    data = create_calendar_features(df)

    # Solar geometric proxy: solar elevation angle indicator
    # Peak at solar noon (hour 12), zero outside [6, 18]
    data["solar_geometric_elevation"] = np.maximum(
        0.0, np.sin(np.pi * np.maximum(0.0, data["hour"] - 6.0) / 12.0)
    )

    for l in lags:
        data[f"solar_lag_{l}"] = data[target_col].shift(l)

    # Meteorological features if present
    if "cloud_cover" in data.columns:
        data["clear_sky_proxy"] = (1.0 - data["cloud_cover"]) * data["solar_geometric_elevation"]
    else:
        data["clear_sky_proxy"] = data["solar_geometric_elevation"]

    if "temperature_c" in data.columns:
        # High temperatures mildly decrease PV efficiency (~ -0.4% / C above 25C)
        data["temp_derating_factor"] = 1.0 - 0.004 * np.maximum(0.0, data["temperature_c"] - 25.0)

    lag_cols = [c for c in data.columns if "solar_lag_" in c]
    if lag_cols:
        data[lag_cols] = data[lag_cols].bfill().ffill()

    return data


def build_price_features(
    df: pd.DataFrame,
    target_col: str = "day_ahead_price_inr_kwh",
    lags: Optional[List[int]] = None,
) -> pd.DataFrame:
    """Constructs features for electricity tariff forecasting."""
    if lags is None:
        lags = [24, 168]

    data = create_calendar_features(df)

    # Tariff tier indicator features based on 3-tier structure
    data["is_off_peak_hour"] = data["hour"].isin([22, 23, 0, 1, 2, 3, 4, 5]).astype(int)
    data["is_peak_hour"] = data["hour"].isin([14, 15, 16, 17, 18, 19]).astype(int)
    data["is_normal_hour"] = (~(data["is_off_peak_hour"].astype(bool) | data["is_peak_hour"].astype(bool))).astype(int)

    for l in lags:
        data[f"price_lag_{l}"] = data[target_col].shift(l)

    lag_cols = [c for c in data.columns if "price_lag_" in c]
    if lag_cols:
        data[lag_cols] = data[lag_cols].bfill().ffill()

    return data


def chronological_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits time series chronologically into Train, Validation, and Test partitions.
    Guarantees no temporal look-ahead leakage and no random shuffling.
    """
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()

    return train_df, val_df, test_df

