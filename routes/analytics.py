"""
GRIDWISE AI - Analytics Blueprint
Monitoring, stochastic scenarios, CVaR risk, BESS, solar PV, and procurement costs.
"""

from flask import Blueprint, render_template, jsonify
from services import MicrogridService, DatasetService, OptimizationService

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/monitoring")
def monitoring_view():
    """Real-time microgrid power flow and telemetry monitoring."""
    config = MicrogridService.get_active_config()
    kpis = DatasetService.get_overview_kpis()
    dataset_stats = DatasetService.get_summary_statistics()
    opt_results = OptimizationService.get_latest_results()

    return render_template(
        "monitoring.html",
        page_title="Campus Microgrid Telemetry & Monitoring",
        active_page="monitoring",
        config=config,
        kpis=kpis,
        dataset_stats=dataset_stats,
        opt_results=opt_results,
    )


@analytics_bp.route("/scenarios")
def scenarios_view():
    """Stochastic scenario generation and distribution interface."""
    config = MicrogridService.get_active_config()
    dataset_stats = DatasetService.get_summary_statistics()
    opt_results = OptimizationService.get_latest_results()

    return render_template(
        "scenarios.html",
        page_title="Stochastic Scenario Generation",
        active_page="scenarios",
        config=config,
        dataset_stats=dataset_stats,
        opt_results=opt_results,
    )


@analytics_bp.route("/risk")
def risk_view():
    """Conditional Value-at-Risk (CVaR) and risk analysis view."""
    config = MicrogridService.get_active_config()
    kpis = DatasetService.get_overview_kpis()
    dataset_stats = DatasetService.get_summary_statistics()
    opt_results = OptimizationService.get_latest_results()

    return render_template(
        "risk.html",
        page_title="Risk & CVaR Frontier Analysis",
        active_page="risk",
        config=config,
        kpis=kpis,
        dataset_stats=dataset_stats,
        opt_results=opt_results,
    )


@analytics_bp.route("/battery")
def battery_view():
    """Battery Energy Storage System (BESS) state and degradation view."""
    config = MicrogridService.get_active_config()
    kpis = DatasetService.get_overview_kpis()
    opt_results = OptimizationService.get_latest_results()

    return render_template(
        "battery.html",
        page_title="Battery Energy Storage System (BESS)",
        active_page="battery",
        config=config,
        kpis=kpis,
        opt_results=opt_results,
    )


@analytics_bp.route("/solar")
def solar_view():
    """Campus Solar PV generation and irradiance forecast analytics."""
    config = MicrogridService.get_active_config()
    kpis = DatasetService.get_overview_kpis()
    dataset_stats = DatasetService.get_summary_statistics()
    opt_results = OptimizationService.get_latest_results()

    return render_template(
        "solar.html",
        page_title="Campus Solar PV Analytics",
        active_page="solar",
        config=config,
        kpis=kpis,
        dataset_stats=dataset_stats,
        opt_results=opt_results,
    )


@analytics_bp.route("/costs")
def costs_view():
    """Day-ahead energy procurement costs and tariff analysis."""
    config = MicrogridService.get_active_config()
    kpis = DatasetService.get_overview_kpis()
    dataset_stats = DatasetService.get_summary_statistics()
    opt_results = OptimizationService.get_latest_results()

    return render_template(
        "costs.html",
        page_title="Energy Procurement & Tariff Analysis",
        active_page="costs",
        config=config,
        kpis=kpis,
        dataset_stats=dataset_stats,
        opt_results=opt_results,
    )


# --- Phase 3, 4, 5 Analytics & Risk JSON API Endpoints ---

@analytics_bp.route("/api/analytics/energy")
def api_analytics_energy():
    """Provides advanced 24-hour energy balance and asset utilization metrics."""
    try:
        from services import EnergyAnalyticsService
        data = EnergyAnalyticsService.get_energy_metrics()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/analytics/battery")
def api_analytics_battery():
    """Provides BESS decision support, SoC conservation, and degradation analytics."""
    try:
        from services import BatteryAnalyticsService
        data = BatteryAnalyticsService.get_battery_analytics()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/analytics/risk")
def api_analytics_risk():
    """Provides scenario-level tail risk metrics, weighted VaR and CVaR distributions."""
    try:
        from services import RiskAnalyticsService
        data = RiskAnalyticsService.get_risk_metrics()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/analytics/cost")
def api_analytics_cost():
    """Provides stochastic vs deterministic cost comparisons, VSS, and EVPI metrics."""
    try:
        from services import CostAnalysisService
        data = CostAnalysisService.get_cost_comparison()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/analytics/sensitivity")
def api_analytics_sensitivity():
    """Provides parametric sensitivity outcomes across operational uncertainty dimensions."""
    try:
        from services import OptimizationService
        data = OptimizationService.get_sensitivity_results()
        return jsonify({"status": "SUCCESS", "sensitivity_results": data, "count": len(data)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/analytics/risk-aversion", methods=["POST"])
def api_analytics_risk_aversion():
    """Evaluates the Mean-CVaR Pareto efficient frontier across lambda values."""
    try:
        from flask import request
        from services import RiskAnalyticsService
        req_data = request.get_json(silent=True) or {}
        lambdas = req_data.get("lambda_values", [0.0, 0.25, 0.50, 0.75, 1.0])
        frontier = RiskAnalyticsService.evaluate_risk_aversion_frontier(lambda_values=lambdas)
        return jsonify({"status": "SUCCESS", "frontier": frontier}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route("/api/dataset/summary")
def api_dataset_summary():
    """Provides high-level dataset statistics across 8760 hours and 500 scenarios."""
    summary = DatasetService.get_summary_statistics()
    return jsonify(summary), 200


@analytics_bp.route("/api/dataset/charts")
def api_dataset_charts():
    """Provides time-series datasets for the 8 Plotly technical charts."""
    charts_data = DatasetService.get_chart_datasets()
    return jsonify(charts_data), 200
