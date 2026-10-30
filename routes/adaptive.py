"""
GRIDWISE AI - Live Energy Intelligence & Adaptive Optimization Routes
Phase 8 Live Weather, Real-Time Forecasting, Adaptive LP Optimization, and Alerts APIs.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
import logging
from flask import Blueprint, render_template, request, jsonify

from services.weather_service import WeatherService
from services.adaptive_forecasting_service import AdaptiveForecastingService
from services.adaptive_optimization_service import (
    AdaptiveOptimizationService,
    AdaptiveAlertsEngine,
)

logger = logging.getLogger(__name__)

adaptive_bp = Blueprint("adaptive", __name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ADAPTIVE_DIR = BASE_DIR / "data" / "adaptive"


# ============================================================================
# PAGE ROUTE: Live Energy Intelligence Dashboard
# ============================================================================

@adaptive_bp.route("/live-intelligence")
@adaptive_bp.route("/adaptive")
def live_intelligence_view():
    """Renders the Live Energy Intelligence & Adaptive Optimization Dashboard."""
    weather = WeatherService.get_weather_data()
    latest_opt = AdaptiveOptimizationService.get_latest_adaptive_results()
    alerts = AdaptiveOptimizationService.get_active_alerts()
    history = AdaptiveOptimizationService.get_adaptive_history(limit=5)

    return render_template(
        "live_intelligence.html",
        active_page="live_intelligence",
        weather=weather,
        latest_opt=latest_opt,
        alerts=alerts,
        history=history,
    )


# ============================================================================
# TASK 7 REST API ENDPOINTS
# ============================================================================

@adaptive_bp.route("/api/live-weather", methods=["GET"])
def api_live_weather():
    """
    GET /api/live-weather
    Returns current weather conditions, 24h hourly forecast, source, and cache status.
    """
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        weather = WeatherService.get_weather_data(latitude=lat, longitude=lon, force_refresh=False)
        return jsonify({"success": True, "data": weather})
    except Exception as e:
        logger.error(f"Error in api_live_weather: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@adaptive_bp.route("/api/weather/refresh", methods=["POST"])
def api_weather_refresh():
    """
    POST /api/weather/refresh
    Forces an immediate live update from Open-Meteo, bypassing the 15-minute cache.
    """
    try:
        data = request.get_json(silent=True) or {}
        lat = data.get("lat")
        lon = data.get("lon")
        weather = WeatherService.refresh_weather(latitude=lat, longitude=lon)
        return jsonify({
            "success": True,
            "message": "Live weather successfully refreshed from Open-Meteo.",
            "data": weather,
        })
    except Exception as e:
        logger.error(f"Error in api_weather_refresh: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@adaptive_bp.route("/api/adaptive/forecast", methods=["GET"])
def api_adaptive_forecast():
    """
    GET /api/adaptive/forecast
    Returns weather-adjusted 24h solar, demand, and electricity price forecasts.
    """
    try:
        force = request.args.get("force_refresh", "false").lower() == "true"
        fc = AdaptiveForecastingService.generate_adaptive_forecasts(force_weather_refresh=force)
        return jsonify({"success": True, "data": fc})
    except Exception as e:
        logger.error(f"Error in api_adaptive_forecast: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@adaptive_bp.route("/api/adaptive/scenarios/generate", methods=["POST"])
def api_adaptive_scenarios_generate():
    """
    POST /api/adaptive/scenarios/generate
    Generates >= 100 weather-conditioned adaptive scenarios.
    """
    try:
        data = request.get_json(silent=True) or {}
        num_scenarios = int(data.get("num_scenarios", 100))
        seed = int(data.get("random_seed", 42))

        summary = AdaptiveForecastingService.generate_adaptive_scenarios(
            num_scenarios=max(10, num_scenarios),
            random_seed=seed,
        )
        return jsonify({
            "success": True,
            "message": f"Successfully generated {summary['num_scenarios']} adaptive scenarios.",
            "data": summary,
        })
    except Exception as e:
        logger.error(f"Error in api_adaptive_scenarios_generate: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@adaptive_bp.route("/api/adaptive/optimize", methods=["POST"])
def api_adaptive_optimize():
    """
    POST /api/adaptive/optimize
    Runs full adaptive workflow: weather -> forecasts -> scenarios -> 2-stage LP -> comparison -> alerts.
    """
    try:
        data = request.get_json(silent=True) or {}
        num_scenarios = int(data.get("num_scenarios", 100))
        risk_lambda = float(data.get("risk_aversion", 0.0))
        batt_cap = float(data.get("battery_capacity_kwh", 1000.0))
        init_soc = float(data.get("initial_soc_pct", 0.50))
        force_weather = bool(data.get("force_weather_refresh", False))

        results = AdaptiveOptimizationService.run_adaptive_optimization(
            num_scenarios=num_scenarios,
            risk_aversion_lambda=risk_lambda,
            battery_capacity_kwh=batt_cap,
            initial_soc_pct=init_soc,
            force_weather_refresh=force_weather,
        )
        return jsonify({
            "success": True,
            "message": "Adaptive stochastic optimization completed successfully.",
            "data": results,
        })
    except Exception as e:
        logger.error(f"Error in api_adaptive_optimize: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@adaptive_bp.route("/api/adaptive/results/latest", methods=["GET"])
def api_adaptive_results_latest():
    """
    GET /api/adaptive/results/latest
    Returns the most recent adaptive optimization solution, schedule, and comparisons.
    """
    results = AdaptiveOptimizationService.get_latest_adaptive_results()
    if results is None:
        return jsonify({"success": False, "error": "No adaptive optimization run found."}), 404
    return jsonify({"success": True, "data": results})


@adaptive_bp.route("/api/adaptive/history", methods=["GET"])
def api_adaptive_history():
    """
    GET /api/adaptive/history
    Returns historical adaptive optimization runs and previous-run delta tracking.
    """
    limit = request.args.get("limit", default=10, type=int)
    history = AdaptiveOptimizationService.get_adaptive_history(limit=limit)
    return jsonify({"success": True, "count": len(history), "data": history})


@adaptive_bp.route("/api/adaptive/alerts", methods=["GET"])
def api_adaptive_alerts():
    """
    GET /api/adaptive/alerts
    Returns active operational, risk, and financial microgrid alerts.
    """
    alerts = AdaptiveOptimizationService.get_active_alerts()
    return jsonify({"success": True, "count": len(alerts), "data": alerts})


@adaptive_bp.route("/api/adaptive/status", methods=["GET"])
def api_adaptive_status():
    """
    GET /api/adaptive/status
    Returns health status of weather cache, adaptive forecasts, and solver engine.
    """
    weather = WeatherService.get_weather_data()
    latest_opt = AdaptiveOptimizationService.get_latest_adaptive_results()
    alerts = AdaptiveOptimizationService.get_active_alerts()

    return jsonify({
        "success": True,
        "status": "OPERATIONAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "weather": {
            "source": weather.get("source"),
            "location": weather.get("location_name"),
            "is_cached": weather.get("is_cached", False),
            "is_stale": weather.get("is_stale", False),
            "fetched_at": weather.get("fetched_at"),
            "current_temp_c": weather.get("current", {}).get("temperature_c"),
        },
        "optimization": {
            "last_run_uuid": latest_opt.get("run_uuid") if latest_opt else None,
            "last_run_date": latest_opt.get("run_date") if latest_opt else None,
            "solver_status": latest_opt.get("solver_status") if latest_opt else None,
            "last_expected_cost_inr": latest_opt.get("expected_cost_inr") if latest_opt else None,
            "vss_inr": latest_opt.get("vss_inr") if latest_opt else None,
        },
        "alerts_count": len(alerts),
    })

