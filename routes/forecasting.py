"""
GRIDWISE AI - Forecasting & Predictive Analytics Routes
Phase 7 Intelligent Predictive Energy Procurement Module
"""

from pathlib import Path
import json
import logging
import pandas as pd
from flask import Blueprint, render_template, request, jsonify

from forecasting.uncertainty_estimator import ForecastUncertaintyEstimator
from services.forecast_optimization_service import ForecastOptimizationService

logger = logging.getLogger(__name__)

forecasting_bp = Blueprint("forecasting", __name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FORECASTS_DIR = BASE_DIR / "data" / "forecasts"
RESULTS_DIR = BASE_DIR / "data" / "results"


@forecasting_bp.route("/forecasting")
def forecasting_page():
    """Renders the Intelligent Energy Forecasting & Predictive Optimization Dashboard."""
    # Load evaluation summary if available
    eval_file = FORECASTS_DIR / "model_evaluation.json"
    evaluation_data = {}
    if eval_file.exists():
        try:
            with open(eval_file, "r") as f:
                evaluation_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading model evaluation json: {e}")

    # Load comparison records if available
    comp_file = FORECASTS_DIR / "model_comparison.csv"
    comparison_table = []
    if comp_file.exists():
        try:
            df_comp = pd.read_csv(comp_file)
            comparison_table = df_comp.to_dict(orient="records")
        except Exception as e:
            logger.error(f"Error reading model comparison csv: {e}")

    # Load latest optimization results if available
    latest_opt = ForecastOptimizationService.get_latest_forecast_optimization_results()

    return render_template(
        "forecasting.html",
        active_page="forecasting",
        evaluation=evaluation_data,
        comparison=comparison_table,
        latest_opt=latest_opt,
    )


@forecasting_bp.route("/api/forecast/demand", methods=["GET"])
def api_forecast_demand():
    """Returns 24h demand point forecast and prediction intervals."""
    file_path = FORECASTS_DIR / "demand_forecast.csv"
    if not file_path.exists():
        return jsonify({"success": False, "error": "Demand forecast not yet generated."}), 404
    try:
        df = pd.read_csv(file_path)
        return jsonify({"success": True, "data": df.to_dict(orient="records")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@forecasting_bp.route("/api/forecast/solar", methods=["GET"])
def api_forecast_solar():
    """Returns 24h solar generation point forecast and prediction intervals."""
    file_path = FORECASTS_DIR / "solar_forecast.csv"
    if not file_path.exists():
        return jsonify({"success": False, "error": "Solar forecast not yet generated."}), 404
    try:
        df = pd.read_csv(file_path)
        return jsonify({"success": True, "data": df.to_dict(orient="records")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@forecasting_bp.route("/api/forecast/prices", methods=["GET"])
def api_forecast_prices():
    """Returns 24h electricity prices (Day-Ahead and Real-Time forecasts)."""
    file_path = FORECASTS_DIR / "price_forecast.csv"
    if not file_path.exists():
        return jsonify({"success": False, "error": "Price forecast not yet generated."}), 404
    try:
        df = pd.read_csv(file_path)
        return jsonify({"success": True, "data": df.to_dict(orient="records")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@forecasting_bp.route("/api/forecast/intervals", methods=["GET"])
def api_forecast_intervals():
    """Returns combined prediction intervals for demand, solar, and prices."""
    file_path = FORECASTS_DIR / "forecast_intervals.csv"
    if not file_path.exists():
        return jsonify({"success": False, "error": "Forecast intervals not found."}), 404
    try:
        df = pd.read_csv(file_path)
        return jsonify({"success": True, "data": df.to_dict(orient="records")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@forecasting_bp.route("/api/forecast/evaluation", methods=["GET"])
def api_forecast_evaluation():
    """Returns full model evaluation, test metrics, and candidate comparison."""
    eval_file = FORECASTS_DIR / "model_evaluation.json"
    comp_file = FORECASTS_DIR / "model_comparison.csv"
    if not eval_file.exists():
        return jsonify({"success": False, "error": "Model evaluation not found."}), 404
    try:
        with open(eval_file, "r") as f:
            eval_data = json.load(f)
        comparison = []
        if comp_file.exists():
            comparison = pd.read_csv(comp_file).to_dict(orient="records")
        return jsonify({"success": True, "evaluation": eval_data, "comparison": comparison})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@forecasting_bp.route("/api/forecast/generate", methods=["POST"])
def api_forecast_generate():
    """Re-trains models and regenerates forecasts and probabilistic scenarios."""
    try:
        data = request.get_json() or {}
        num_scenarios = int(data.get("num_scenarios", 50))
        estimator = ForecastUncertaintyEstimator()
        result = estimator.generate_all_forecasts(num_scenarios=num_scenarios)
        return jsonify({
            "success": True,
            "message": f"Successfully generated forecasts and {num_scenarios} probabilistic scenarios.",
            "details": result,
        })
    except Exception as e:
        logger.error(f"Error generating forecasts: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@forecasting_bp.route("/api/forecast/optimize", methods=["POST"])
def api_forecast_optimize():
    """Executes predictive forecast-driven two-stage stochastic optimization."""
    try:
        data = request.get_json() or {}
        num_scenarios = int(data.get("num_scenarios", 50))
        risk_aversion = float(data.get("risk_aversion", 0.0))
        battery_capacity = float(data.get("battery_capacity_kwh", 1000.0))
        initial_soc = float(data.get("initial_soc_pct", 0.50))

        result = ForecastOptimizationService.run_forecast_optimization(
            num_scenarios=num_scenarios,
            risk_aversion_lambda=risk_aversion,
            battery_capacity_kwh=battery_capacity,
            initial_soc_pct=initial_soc,
        )
        return jsonify({
            "success": True,
            "message": "Predictive forecast stochastic optimization completed successfully.",
            "data": result,
        })
    except Exception as e:
        logger.error(f"Error running forecast optimization: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@forecasting_bp.route("/api/forecast/optimization-results", methods=["GET"])
def api_forecast_optimization_results():
    """Fetches latest predictive optimization results."""
    res = ForecastOptimizationService.get_latest_forecast_optimization_results()
    if res is None:
        return jsonify({"success": False, "error": "No forecast optimization run found."}), 404
    return jsonify({"success": True, "data": res})

