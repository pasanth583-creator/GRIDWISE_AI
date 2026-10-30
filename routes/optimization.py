"""
GRIDWISE AI - Optimization Blueprint
Day-ahead stochastic optimization view, parameter configuration, real-time solver execution, and dispatch control.
"""

import logging
from flask import Blueprint, render_template, jsonify, request
from services import MicrogridService, OptimizationService
from optimization import FormulationType, SolverMethod

logger = logging.getLogger(__name__)

optimization_bp = Blueprint("optimization", __name__)


@optimization_bp.route("/optimization")
def optimization_view():
    """Stochastic optimization interface and dispatch control."""
    config = MicrogridService.get_active_config()
    latest_run = MicrogridService.get_latest_optimization_run()
    recent_runs = MicrogridService.get_optimization_runs_list(limit=10)
    opt_results = OptimizationService.get_latest_results()

    formulations = [f.value for f in FormulationType]
    solvers = [s.value for s in SolverMethod]

    return render_template(
        "optimization.html",
        page_title="Day-Ahead Stochastic Optimization",
        active_page="optimization",
        config=config,
        latest_run=latest_run,
        recent_runs=recent_runs,
        formulations=formulations,
        solvers=solvers,
        opt_results=opt_results,
    )


@optimization_bp.route("/api/optimization/run", methods=["POST"])
def run_optimization_api():
    """
    Executes real two-stage stochastic optimization solver on demand.
    Accepts JSON payload with configuration parameters.
    """
    try:
        data = request.get_json(silent=True) or {}
        num_scenarios = int(data.get("num_scenarios", 500))
        risk_lambda = float(data.get("risk_aversion", 0.0))
        bess_cap = float(data.get("battery_capacity_kwh", 1000.0))
        max_charge = float(data.get("max_charge_kw", bess_cap * 0.4))
        max_discharge = float(data.get("max_discharge_kw", bess_cap * 0.4))
        initial_soc = float(data.get("initial_soc_pct", 0.50))

        # Clamp parameters to valid physical envelopes
        num_scenarios = max(5, min(500, num_scenarios))
        risk_lambda = max(0.0, min(1.0, risk_lambda))
        bess_cap = max(100.0, min(5000.0, bess_cap))

        logger.info(f"API Triggered Stochastic Optimization: N={num_scenarios}, lambda={risk_lambda}")
        result = OptimizationService.run_optimization(
            num_scenarios=num_scenarios,
            risk_aversion_lambda=risk_lambda,
            battery_capacity_kwh=bess_cap,
            max_charge_kw=max_charge,
            max_discharge_kw=max_discharge,
            initial_soc_pct=initial_soc,
        )

        return jsonify({
            "success": True,
            "message": "Optimization solved to numerical optimality successfully.",
            "results": result,
        }), 200

    except Exception as e:
        logger.error(f"Error executing optimization API: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Optimization solve failed: {e}",
        }), 500


@optimization_bp.route("/api/optimization/latest")
def get_latest_results_api():
    """Returns the latest optimization run summary and dispatch series."""
    try:
        results = OptimizationService.get_latest_results()
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@optimization_bp.route("/api/optimization/sensitivity")
def get_sensitivity_api():
    """Returns parametric sensitivity results."""
    try:
        data = OptimizationService.get_sensitivity_results()
        return jsonify({"sensitivity_results": data, "count": len(data)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@optimization_bp.route("/api/optimization/runs")
def list_runs():
    """API endpoint to get list of optimization runs."""
    limit = request.args.get("limit", 10, type=int)
    runs = MicrogridService.get_optimization_runs_list(limit=limit)
    return jsonify({"runs": runs, "count": len(runs)}), 200


@optimization_bp.route("/api/optimization/parameters")
def get_parameters():
    """API endpoint returning optimization solver parameter schema."""
    config = MicrogridService.get_active_config()
    return jsonify({
        "defaults": {
            "num_scenarios": 500,
            "confidence_alpha": 0.95,
            "risk_weight_lambda": 0.0,
            "formulation": FormulationType.TWO_STAGE_STOCHASTIC.value,
            "solver": SolverMethod.HIGHS_INTERIOR_POINT.value,
        },
        "formulations": [f.value for f in FormulationType],
        "solvers": [s.value for s in SolverMethod],
        "microgrid_config": config.to_dict(),
    }), 200
