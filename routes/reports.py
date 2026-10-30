"""
GRIDWISE AI - Reports & Model Formulation Blueprint
PDF/CSV reports export and mathematical optimization formulation reference.
"""

from flask import Blueprint, render_template, jsonify, request, Response
from services import MicrogridService, DatasetService, ReportService

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports")
def reports_view():
    """Reporting center for generating dispatch audit reports and summaries."""
    config = MicrogridService.get_active_config()
    latest_run = MicrogridService.get_latest_optimization_run()
    recent_runs = MicrogridService.get_optimization_runs_list(limit=10)
    dataset_stats = DatasetService.get_summary_statistics()

    return render_template(
        "reports.html",
        page_title="Executive Reports & Export Center",
        active_page="reports",
        config=config,
        latest_run=latest_run,
        recent_runs=recent_runs,
        dataset_stats=dataset_stats,
    )


@reports_bp.route("/model")
def model_view():
    """Mathematical formulation of the two-stage stochastic optimization model."""
    config = MicrogridService.get_active_config()
    dataset_stats = DatasetService.get_summary_statistics()

    return render_template(
        "model.html",
        page_title="Optimization Mathematical Formulation",
        active_page="model",
        config=config,
        dataset_stats=dataset_stats,
    )


@reports_bp.route("/reports/download/pdf")
def download_pdf_report():
    """Compiles and streams the complete 12-section technical dispatch audit PDF."""
    try:
        report_type = request.args.get("type", "executive")
        pdf_bytes = ReportService.generate_pdf_report()
        filename = f"GRIDWISE_Dispatch_Audit_Report_{report_type}.pdf"

        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache",
            },
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "message": f"Failed to generate PDF: {e}"}), 500


@reports_bp.route("/reports/download/csv")
def download_csv_export():
    """Generates and streams structured CSV tabular audit downloads."""
    report_type = request.args.get("type", "hourly")
    try:
        csv_content, filename = ReportService.export_results_csv(report_type)
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache",
            },
        )
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve), "message": f"Invalid export type: {ve}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "message": f"Failed to export CSV: {e}"}), 500


@reports_bp.route("/api/reports/specs")
def reports_specs():
    """Returns microgrid specifications for report generation."""
    config = MicrogridService.get_active_config()
    return jsonify({
        "microgrid_config": config.to_dict(),
        "report_engine": "ReportLab 5.x",
        "supported_formats": ["PDF", "CSV", "JSON"],
        "endpoints": {
            "pdf_download": "/reports/download/pdf?type=executive",
            "csv_downloads": {
                "hourly_schedule": "/reports/download/csv?type=hourly",
                "scenario_costs": "/reports/download/csv?type=scenarios",
                "deterministic_baseline": "/reports/download/csv?type=baseline",
                "sensitivity_analysis": "/reports/download/csv?type=sensitivity",
                "risk_metrics": "/reports/download/csv?type=risk",
            },
        },
    }), 200
