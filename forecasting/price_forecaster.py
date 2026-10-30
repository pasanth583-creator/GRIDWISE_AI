"""
GRIDWISE AI - Electricity Tariff and Spot Price Forecaster
Implements Historical Baseline, Linear Regression, Random Forest, and Gradient Boosting.
Predicts 24-hour ahead Day-Ahead wholesale and Real-Time balancing spot prices.
"""

from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

from forecasting.feature_engineering import build_price_features, chronological_split
from forecasting.evaluation import compute_metrics
from forecasting.prediction_intervals import PredictionIntervalEstimator

BASE_DIR = Path(__file__).resolve().parent.parent


class HistoricalPriceBaseline:
    """Historical tariff baseline: averages historical price grouped by (hour, is_weekend)."""

    def __init__(self):
        self.lookup_table: Dict[Tuple[int, int], float] = {}
        self.global_mean = 7.50

    def fit(self, X: pd.DataFrame, y: pd.Series):
        df = X.copy()
        df["target"] = y.values
        self.global_mean = float(y.mean())
        grouped = df.groupby(["hour", "is_weekend"])["target"].mean().to_dict()
        self.lookup_table = {k: float(v) for k, v in grouped.items()}

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in X.iterrows():
            k = (int(row["hour"]), int(row["is_weekend"]))
            preds.append(self.lookup_table.get(k, self.global_mean))
        return np.array(preds)


class ElectricityPriceForecaster:
    """Predicts Day-Ahead and Real-Time spot tariffs across 24 hourly dispatch periods."""

    FEATURE_COLS = [
        "hour", "hour_sin", "hour_cos",
        "day_of_week", "is_weekend", "month",
        "is_off_peak_hour", "is_peak_hour", "is_normal_hour",
        "price_lag_24", "price_lag_168",
    ]

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.models = {
            "Historical Baseline": HistoricalPriceBaseline(),
            "Linear Regression (Ridge)": Ridge(alpha=10.0, random_state=random_state),
            "Random Forest": RandomForestRegressor(n_estimators=100, max_depth=10, random_state=random_state, n_jobs=-1),
            "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.08, random_state=random_state),
        }
        self.best_model_name = "Gradient Boosting"
        self.best_model = None
        self.validation_results: Dict[str, Dict[str, float]] = {}
        self.test_metrics: Dict[str, float] = {}
        self.interval_estimator = PredictionIntervalEstimator(confidence_level=0.90)

    def train_and_evaluate(self, raw_price_df: pd.DataFrame, target_col: str = "real_time_price_inr_kwh") -> Dict[str, Any]:
        """
        Trains and validates electricity price prediction models.
        """
        feat_df = build_price_features(raw_price_df, target_col=target_col)
        train_df, val_df, test_df = chronological_split(feat_df, train_ratio=0.70, val_ratio=0.15)

        X_train = train_df[self.FEATURE_COLS].copy()
        y_train = train_df[target_col].values

        X_val = val_df[self.FEATURE_COLS].copy()
        y_val = val_df[target_col].values

        X_test = test_df[self.FEATURE_COLS].copy()
        y_test = test_df[target_col].values

        self.scaler.fit(X_train)
        X_train_scaled = self.scaler.transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)

        best_val_rmse = float("inf")

        for name, model in self.models.items():
            if name == "Historical Baseline":
                model.fit(X_train, train_df[target_col])
                val_preds = model.predict(X_val)
            elif name == "Linear Regression (Ridge)":
                model.fit(X_train_scaled, y_train)
                val_preds = model.predict(X_val_scaled)
            else:
                model.fit(X_train, y_train)
                val_preds = model.predict(X_val)

            # Strictly positive prices (> ₹1.0 / kWh)
            val_preds = np.maximum(1.0, val_preds)
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

        test_preds = np.maximum(1.0, test_preds)
        val_preds_best = np.maximum(1.0, val_preds_best)

        self.interval_estimator.fit(y_val, val_preds_best, hours=val_df["hour"].values)
        test_lower, test_upper = self.interval_estimator.predict_intervals(
            test_preds, hours=test_df["hour"].values, min_clip=1.0
        )

        self.test_metrics = compute_metrics(y_test, test_preds, test_lower, test_upper)

        return {
            "target": target_col,
            "selected_model": self.best_model_name,
            "validation_comparison": self.validation_results,
            "test_metrics": self.test_metrics,
        }

    def predict_next_24h(self, recent_history_df: pd.DataFrame, target_col: str = "real_time_price_inr_kwh") -> pd.DataFrame:
        """
        Generates 24-hour ahead electricity tariff and balancing price predictions.
        """
        if self.best_model is None:
            raise RuntimeError("Price forecaster must be trained before predicting.")

        feat_df = build_price_features(recent_history_df, target_col=target_col)
        last_24 = feat_df.tail(24).copy().reset_index(drop=True)
        X_pred = last_24[self.FEATURE_COLS]

        if self.best_model_name == "Historical Baseline":
            preds = self.best_model.predict(X_pred)
        elif self.best_model_name == "Linear Regression (Ridge)":
            X_scaled = self.scaler.transform(X_pred)
            preds = self.best_model.predict(X_scaled)
        else:
            preds = self.best_model.predict(X_pred)

        preds = np.maximum(1.0, preds)
        hours = last_24["hour"].values
        lower, upper = self.interval_estimator.predict_intervals(preds, hours=hours, min_clip=1.0)

        out_df = pd.DataFrame({
            "hour": hours,
            f"predicted_{target_col}": np.round(preds, 2),
            "price_ci_lower_inr_kwh": np.round(lower, 2),
            "price_ci_upper_inr_kwh": np.round(upper, 2),
        })
        return out_df

