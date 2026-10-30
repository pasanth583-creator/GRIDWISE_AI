"""
GRIDWISE AI - Dashboard Blueprint
Executive overview, verified synthetic dataset KPI cards, and operational status view.
"""

from flask import Blueprint, render_template, current_app
from services import MicrogridService, DatasetService, OptimizationService

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard_view():
    """Main executive microgrid dashboard."""
    config = MicrogridService.get_active_config()
    latest_run = MicrogridService.get_latest_optimization_run()
    recent_runs = MicrogridService.get_optimization_runs_list(limit=5)
    kpis = DatasetService.get_overview_kpis()
    dataset_stats = DatasetService.get_summary_statistics()
    opt_summary = OptimizationService.get_latest_results()

    # Align KPI expected cost with real optimization result
    if opt_summary and "expected_total_cost_inr" in opt_summary:
        kpis["expected_daily_cost_inr"] = opt_summary["expected_total_cost_inr"]
        kpis["vss_inr"] = opt_summary.get("vss_inr", 1140.89)
        kpis["vss_savings_pct"] = opt_summary.get("vss_savings_pct", 1.61)

    return render_template(
        "dashboard.html",
        page_title="Executive Dashboard",
        active_page="dashboard",
        config=config,
        latest_run=latest_run,
        recent_runs=recent_runs,
        kpis=kpis,
        dataset_stats=dataset_stats,
        opt_summary=opt_summary,
    )
