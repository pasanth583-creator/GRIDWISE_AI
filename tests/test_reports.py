"""
Tests for Phase 5 Automated Technical Audit and Export Engine.
Verifies ReportLab PDF generation, CSV tabular data exports,
and Flask download routes.
"""

import pytest
import io
from app import create_app
from services import ReportService


@pytest.fixture
def app():
    """Create Flask application test instance."""
    app_instance = create_app("testing")
    yield app_instance


@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()


class TestReportService:
    """Validates ReportLab PDF generation and CSV exports."""

    def test_generate_technical_audit_pdf(self):
        pdf_buffer = ReportService.generate_technical_audit_pdf()
        assert isinstance(pdf_buffer, io.BytesIO)
        content = pdf_buffer.getvalue()
        assert len(content) > 1000
        # Valid PDF files start with %PDF
        assert content.startswith(b"%PDF")

    def test_export_results_csv_types(self):
        csv_types = ["hourly", "scenarios", "baseline", "sensitivity", "risk"]
        for ctype in csv_types:
            csv_str, filename = ReportService.export_results_csv(ctype)
            assert isinstance(csv_str, str)
            assert len(csv_str) > 0
            assert filename.endswith(".csv")
            assert "\n" in csv_str

    def test_export_results_csv_invalid_type(self):
        with pytest.raises(ValueError, match="Unknown CSV export type"):
            ReportService.export_results_csv("non_existent_type")


class TestReportRoutes:
    """Validates HTTP endpoints for downloading reports."""

    def test_download_pdf_route(self, client):
        resp = client.get("/reports/download/pdf")
        assert resp.status_code == 200
        assert resp.content_type == "application/pdf"
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        assert resp.data.startswith(b"%PDF")

    def test_download_csv_route_valid(self, client):
        for ctype in ["hourly", "scenarios", "baseline", "sensitivity", "risk"]:
            resp = client.get(f"/reports/download/csv?type={ctype}")
            assert resp.status_code == 200
            assert "text/csv" in resp.content_type
            assert len(resp.data) > 0

    def test_download_csv_route_invalid(self, client):
        resp = client.get("/reports/download/csv?type=invalid_type")
        assert resp.status_code == 400
        assert b"error" in resp.data

