"""
GRIDWISE AI - Prediction Interval & Uncertainty Estimation Module
Estimates empirical confidence and prediction intervals for 24-hour ahead forecasts
using validation residual distributions and time-dependent quantile mapping.
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import pandas as pd


class PredictionIntervalEstimator:
    """Estimates empirical prediction intervals based on out-of-sample validation residuals."""

    def __init__(self, confidence_level: float = 0.90):
        self.confidence_level = confidence_level
        self.alpha = 1.0 - confidence_level
        self.lower_quantile = self.alpha / 2.0
        self.upper_quantile = 1.0 - (self.alpha / 2.0)
        self.global_residual_lower = 0.0
        self.global_residual_upper = 0.0
        self.hourly_residual_quantiles: Dict[int, Tuple[float, float]] = {}

    def fit(self, y_true: np.ndarray, y_pred: np.ndarray, hours: Optional[np.ndarray] = None) -> "PredictionIntervalEstimator":
        """
        Fits empirical residual quantiles from validation errors (y_true - y_pred).
        """
        residuals = np.asarray(y_true) - np.asarray(y_pred)
        self.global_residual_lower = float(np.percentile(residuals, self.lower_quantile * 100.0))
        self.global_residual_upper = float(np.percentile(residuals, self.upper_quantile * 100.0))

        if hours is not None:
            df_res = pd.DataFrame({"residual": residuals, "hour": hours})
            for h, group in df_res.groupby("hour"):
                res_h = group["residual"].values
                if len(res_h) > 5:
                    q_low = float(np.percentile(res_h, self.lower_quantile * 100.0))
                    q_high = float(np.percentile(res_h, self.upper_quantile * 100.0))
                else:
                    q_low = self.global_residual_lower
                    q_high = self.global_residual_upper
                self.hourly_residual_quantiles[int(h)] = (q_low, q_high)

        return self

    def predict_intervals(
        self,
        y_pred: np.ndarray,
        hours: Optional[np.ndarray] = None,
        min_clip: Optional[float] = 0.0,
        max_clip: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Applies learned residual quantiles to future point forecasts to construct lower and upper bounds.
        """
        yp = np.asarray(y_pred, dtype=float)
        n = len(yp)
        lower_bounds = np.zeros(n)
        upper_bounds = np.zeros(n)

        for i in range(n):
            h = int(hours[i]) if (hours is not None and i < len(hours)) else (i % 24)
            if h in self.hourly_residual_quantiles:
                q_low, q_high = self.hourly_residual_quantiles[h]
            else:
                q_low, q_high = self.global_residual_lower, self.global_residual_upper

            lower_bounds[i] = yp[i] + q_low
            upper_bounds[i] = yp[i] + q_high

        # Enforce physical clipping
        if min_clip is not None:
            lower_bounds = np.maximum(min_clip, lower_bounds)
            upper_bounds = np.maximum(min_clip, upper_bounds)

        if max_clip is not None:
            lower_bounds = np.minimum(max_clip, lower_bounds)
            upper_bounds = np.minimum(max_clip, upper_bounds)

        # Guarantee lower <= upper
        lower_bounds = np.minimum(lower_bounds, upper_bounds)

        return lower_bounds, upper_bounds


def compute_empirical_residuals(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """Computes empirical errors/residuals (y_true - y_pred)."""
    return np.asarray(y_true) - np.asarray(y_pred)

