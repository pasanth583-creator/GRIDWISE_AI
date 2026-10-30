"""
GRIDWISE AI - Time Series Forecasting Model Evaluation Module
Calculates standard deterministic and probabilistic evaluation metrics:
MAE, RMSE, MAPE, WAPE, R-squared, PICP, and PINAW.
"""

from typing import Dict, Any, Union
import numpy as np


def compute_metrics(
    y_true: Union[np.ndarray, list],
    y_pred: Union[np.ndarray, list],
    y_lower: Union[np.ndarray, list, None] = None,
    y_upper: Union[np.ndarray, list, None] = None,
    eps: float = 1e-4,
) -> Dict[str, float]:
    """
    Computes standard point-forecast and prediction-interval evaluation metrics.
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)

    diff = yt - yp
    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(np.mean(diff ** 2)))

    # WAPE (Weighted Absolute Percentage Error) - highly robust to near-zero actuals
    denom = np.sum(np.abs(yt))
    wape = float(np.sum(np.abs(diff)) / denom * 100.0) if denom > eps else 0.0

    # MAPE computed on non-zero subset
    nz_mask = np.abs(yt) > 1.0  # safe threshold (e.g. > 1 kWh)
    if np.any(nz_mask):
        mape = float(np.mean(np.abs(diff[nz_mask] / yt[nz_mask])) * 100.0)
    else:
        mape = wape

    # R-squared
    ss_tot = np.sum((yt - np.mean(yt)) ** 2)
    ss_res = np.sum(diff ** 2)
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > eps else 0.0

    metrics = {
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "mape_pct": round(mape, 2),
        "wape_pct": round(wape, 2),
        "r2_score": round(r2, 4),
    }

    # Prediction Interval evaluation if bounds provided
    if y_lower is not None and y_upper is not None:
        yl = np.asarray(y_lower, dtype=float)
        yu = np.asarray(y_upper, dtype=float)

        # PICP: Prediction Interval Coverage Probability (fraction of actuals inside [yl, yu])
        covered = (yt >= yl) & (yt <= yu)
        picp = float(np.mean(covered) * 100.0)

        # PINAW: Prediction Interval Normalized Average Width
        data_range = float(np.max(yt) - np.min(yt))
        if data_range > eps:
            pinaw = float(np.mean(yu - yl) / data_range * 100.0)
        else:
            pinaw = float(np.mean(yu - yl))

        metrics["picp_coverage_pct"] = round(picp, 2)
        metrics["pinaw_width_pct"] = round(pinaw, 2)

    return metrics


def compute_interval_metrics(
    y_true: Union[np.ndarray, list],
    y_lower: Union[np.ndarray, list],
    y_upper: Union[np.ndarray, list],
    eps: float = 1e-4,
) -> Dict[str, float]:
    """Computes PICP and PINAW interval metrics."""
    yt = np.asarray(y_true, dtype=float)
    yl = np.asarray(y_lower, dtype=float)
    yu = np.asarray(y_upper, dtype=float)

    covered = (yt >= yl) & (yt <= yu)
    picp = float(np.mean(covered) * 100.0)
    data_range = float(np.max(yt) - np.min(yt))
    pinaw = float(np.mean(yu - yl) / data_range * 100.0) if data_range > eps else float(np.mean(yu - yl))

    return {
        "picp_coverage_pct": round(picp, 2),
        "pinaw_width_pct": round(pinaw, 2),
    }


def evaluate_point_forecast(y_true: Union[np.ndarray, list], y_pred: Union[np.ndarray, list]) -> Dict[str, float]:
    """Convenience alias for computing point metrics."""
    return compute_metrics(y_true, y_pred)


def format_metrics_table(metrics_dict: Dict[str, Dict[str, float]]) -> str:
    """Formats a dictionary of model metrics as a clean markdown table."""
    headers = ["Model / Target", "MAE", "RMSE", "MAPE (%)", "WAPE (%)", "R²"]
    rows = []
    for model_name, m in metrics_dict.items():
        rows.append(
            f"| {model_name} | {m.get('mae', '-')} | {m.get('rmse', '-')} | "
            f"{m.get('mape_pct', '-')} | {m.get('wape_pct', '-')} | {m.get('r2_score', '-')} |"
        )
    header_str = "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n"
    return header_str + "\n".join(rows)

