"""
GRIDWISE AI - Solar Photovoltaic Generation Forecaster
Implements Historical Baseline, Linear Regression, Random Forest, and Gradient Boosting.
Enforces physical solar invariants: non-negativity, nighttime zero, and 800 kWp capacity limit.
"""

from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

from forecasting.feature_engineering import build_solar_features, chronological_split
from forecasting.evaluation import compute_metrics
from forecasting.prediction_intervals import PredictionIntervalEstimator

BASE_DIR = Path(__file__).resolve().parent.parent


class HistoricalSolarBaseline:
    """Historical solar baseline: averages historical generation grouped by (hour, month)."""

    def __init__(self):
        self.lookup_table: Dict[Tuple[int, int], float] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series):
        df = X.copy()
        df["target"] = y.values
        grouped = df.groupby(["hour", "month"])["target"].mean().to_dict()
        self.lookup_table = {k: float(v) for k, v in grouped.items()}

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in X.iterrows():
            k = (int(row["hour"]), int(row["month"]))
            preds.append(self.lookup_table.get(k, 0.0))
        return np.array(preds)


class SolarGenerationForecaster:
    """Orchestrates solar model training, physical post-processing, and 24-hour generation forecasting."""

    FEATURE_COLS = [
        "hour", "hour_sin", "hour_cos",
        "month", "month_sin", "month_cos",
        "solar_geometric_elevation", "clear_sky_proxy",
        "solar_lag_24", "solar_lag_48",
    ]
    CAPACITY_KWP = 800.0
    NIGHT_HOURS = {0, 1, 2, 3, 4, 5, 20, 21, 22, 23}

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.models = {
            "Historical Baseline": HistoricalSolarBaseline(),
            "Linear Regression (Ridge)": Ridge(alpha=10.0, random_state=random_state),
            "Random Forest": RandomForestRegressor(n_estimators=100, max_depth=10, random_state=random_state, n_jobs=-1),
            "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.08, random_state=random_state),
        }
        self.best_model_name = "Gradient Boosting"
        self.best_model = None
        self.validation_results: Dict[str, Dict[str, float]] = {}
        self.test_metrics: Dict[str, float] = {}
        self.interval_estimator = PredictionIntervalEstimator(confidence_level=0.90)

    @classmethod
    def enforce_physical_constraints(cls, predictions: np.ndarray, hours: np.ndarray, max_capacity: float = 800.0) -> np.ndarray:
        """
        Applies physical boundary enforcement:
        1. Non-negativity (generation cannot be negative).
        2. Installed capacity ceiling (capped at max_capacity kWp, default 800).
        3. Nighttime zero enforcement (hours 20 to 5 are strictly 0.0).
        """
        preds = np.asarray(predictions, dtype=float).copy()
        preds = np.clip(preds, 0.0, max_capacity)
        for i, h in enumerate(hours):
            if int(h) in cls.NIGHT_HOURS:
                preds[i] = 0.0
        return preds

    def train_and_evaluate(self, raw_solar_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Trains models on chronological train set, selects best on validation set, and evaluates on test set.
        """
        feat_df = build_solar_features(raw_solar_df)
        train_df, val_df, test_df = chronological_split(feat_df, train_ratio=0.70, val_ratio=0.15)

        X_train = train_df[self.FEATURE_COLS].copy()
        y_train = train_df["solar_generation_kwh"].values

        X_val = val_df[self.FEATURE_COLS].copy()
        y_val = val_df["solar_generation_kwh"].values

        X_test = test_df[self.FEATURE_COLS].copy()
        y_test = test_df["solar_generation_kwh"].values

        self.scaler.fit(X_train)
        X_train_scaled = self.scaler.transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)

        best_val_rmse = float("inf")

        for name, model in self.models.items():
            if name == "Historical Baseline":
                model.fit(X_train, train_df["solar_generation_kwh"])
                val_preds = model.predict(X_val)
            elif name == "Linear Regression (Ridge)":
                model.fit(X_train_scaled, y_train)
                val_preds = model.predict(X_val_scaled)
            else:
                model.fit(X_train, y_train)
                val_preds = model.predict(X_val)

            val_preds = self.enforce_physical_constraints(val_preds, val_df["hour"].values)
            m = compute_metrics(y_val, val_preds)
            self.validation_results[name] = m

            if m["rmse"] < best_val_rmse:
                best_val_rmse = m["rmse"]
                self.best_model_name = name
                self.best_model = model

        # Evaluate best model on test set
        if self.best_model_name == "Historical Baseline":
            test_preds = self.best_model.predict(X_test)
            val_preds_best = self.best_model.predict(X_val)
        elif self.best_model_name == "Linear Regression (Ridge)":
            test_preds = self.best_model.predict(X_test_scaled)
            val_preds_best = self.best_model.predict(X_val_scaled)
        else:
            test_preds = self.best_model.predict(X_test)
            val_preds_best = self.best_model.predict(X_val)

        test_preds = self.enforce_physical_constraints(test_preds, test_df["hour"].values)
        val_preds_best = self.enforce_physical_constraints(val_preds_best, val_df["hour"].values)

        # Fit prediction intervals
        self.interval_estimator.fit(y_val, val_preds_best, hours=val_df["hour"].values)
        test_lower, test_upper = self.interval_estimator.predict_intervals(
            test_preds, hours=test_df["hour"].values, min_clip=0.0, max_clip=self.CAPACITY_KWP
        )
        test_lower = self.enforce_physical_constraints(test_lower, test_df["hour"].values)
        test_upper = self.enforce_physical_constraints(test_upper, test_df["hour"].values)

        self.test_metrics = compute_metrics(y_test, test_preds, test_lower, test_upper)

        return {
            "selected_model": self.best_model_name,
            "validation_comparison": self.validation_results,
            "test_metrics": self.test_metrics,
        }

    def predict_next_24h(self, recent_history_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates 24-hour ahead solar generation forecast respecting physical capacity and nighttime zeros.
        """
        if self.best_model is None:
            raise RuntimeError("Solar forecaster must be trained before predicting.")

        feat_df = build_solar_features(recent_history_df)
        last_24 = feat_df.tail(24).copy().reset_index(drop=True)
        X_pred = last_24[self.FEATURE_COLS]

        if self.best_model_name == "Historical Baseline":
            preds = self.best_model.predict(X_pred)
        elif self.best_model_name == "Linear Regression (Ridge)":
            X_scaled = self.scaler.transform(X_pred)
            preds = self.best_model.predict(X_scaled)
        else:
            preds = self.best_model.predict(X_pred)

        hours = last_24["hour"].values
        preds = self.enforce_physical_constraints(preds, hours)

        lower, upper = self.interval_estimator.predict_intervals(
            preds, hours=hours, min_clip=0.0, max_clip=self.CAPACITY_KWP
        )
        lower = self.enforce_physical_constraints(lower, hours)
        upper = self.enforce_physical_constraints(upper, hours)

        out_df = pd.DataFrame({
            "hour": hours,
            "predicted_solar_kwh": np.round(preds, 2),
            "solar_ci_lower_kwh": np.round(lower, 2),
            "solar_ci_upper_kwh": np.round(upper, 2),
        })
        return out_df
