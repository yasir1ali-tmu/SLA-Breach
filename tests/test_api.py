"""Unit and integration tests for FastAPI backend and REST API endpoints."""

import io
from unittest.mock import patch
import docx
from fastapi.testclient import TestClient
import pytest

from config.settings import AppSettings
from web.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a fresh TestClient instance."""
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    """GET /api/health should return 200 OK with system status, version, and timestamp."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "app" in data
    assert "timestamp" in data


def test_rules_endpoint(client: TestClient) -> None:
    """GET /api/rules should return active configuration thresholds and constraints."""
    response = client.get("/api/rules")
    assert response.status_code == 200
    data = response.json()
    assert "sla_thresholds" in data
    assert "severity_rules" in data
    assert "column_mappings" in data
    assert "allowed_extensions" in data
    assert "max_upload_size_mb" in data
    assert ".html" in data["allowed_extensions"]
    assert ".docx" in data["allowed_extensions"]
    assert data["max_upload_size_mb"] > 0


def test_upload_html_success(client: TestClient) -> None:
    """POST /api/upload with valid HTML table extracts records and computes SLA metrics."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <body>
        <h2>Active Incidents</h2>
        <table>
            <tr>
                <th>Key</th>
                <th>Summary</th>
                <th>Priority</th>
                <th>Created</th>
                <th>Team</th>
            </tr>
            <tr>
                <td>INC-101</td>
                <td>Database connectivity outage</td>
                <td>P1</td>
                <td>2026-10-01 10:00:00</td>
                <td>Infrastructure</td>
            </tr>
            <tr>
                <td>INC-102</td>
                <td>Minor UI layout glitch in navbar</td>
                <td>P4</td>
                <td>2026-10-12 09:30:00</td>
                <td>Frontend</td>
            </tr>
        </table>
    </body>
    </html>
    """
    file_bytes = io.BytesIO(html_content.encode("utf-8"))
    response = client.post(
        "/api/upload",
        files={"file": ("incidents.html", file_bytes, "text/html")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["source_filename"] == "incidents.html"
    assert data["file_type"] == "html"
    assert data["total_rows"] == 2
    assert data["parsed_count"] == 2
    assert data["unparsed_rows"] == 0
    assert len(data["errors"]) == 0
    assert data["metrics"]["total_records"] == 2

    records = data["records"]
    assert len(records) == 2
    rec1 = next(r for r in records if r["key"] == "INC-101")
    assert rec1["summary"] == "Database connectivity outage"
    assert rec1["team"] == "Infrastructure"
    assert rec1["sla_target_days"] == 1.0
    assert rec1["elapsed_days"] is not None
    assert rec1["overdue_days"] is not None
    assert rec1["severity"] in ["OK", "WARNING", "CRITICAL", "BREACHED"]

    # Validate analytics payload structure
    assert "analytics" in data
    analytics = data["analytics"]
    assert "overdue_distribution" in analytics
    assert all(
        k in analytics["overdue_distribution"]
        for k in ["0-1d", "1-3d", "3-7d", ">7d"]
    )
    assert "severity_distribution" in analytics
    assert all(
        k in analytics["severity_distribution"]
        for k in ["OK", "WARNING", "CRITICAL", "BREACHED"]
    )
    assert "team_rankings" in analytics
    assert isinstance(analytics["team_rankings"], list)
    assert len(analytics["team_rankings"]) > 0
    assert "team" in analytics["team_rankings"][0]
    assert "breached" in analytics["team_rankings"][0]


def test_upload_htm_extension_success(client: TestClient) -> None:
    """POST /api/upload supports .htm extension as valid HTML."""
    htm_content = """
    <table>
        <tr><th>Ticket ID</th><th>Issue summary</th><th>Priority</th></tr>
        <tr><td>SEC-404</td><td>Firewall rule update</td><td>P2</td></tr>
    </table>
    """
    file_bytes = io.BytesIO(htm_content.encode("utf-8"))
    response = client.post(
        "/api/upload",
        files={"file": ("report.htm", file_bytes, "text/html")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["parsed_count"] == 1
    assert data["records"][0]["key"] == "SEC-404"


def test_upload_docx_success(client: TestClient) -> None:
    """POST /api/upload parses DOCX table into calculated SLA records."""
    doc = docx.Document()
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Issue Key"
    hdr_cells[1].text = "Description"
    hdr_cells[2].text = "Priority"
    hdr_cells[3].text = "Created Date"

    row_cells = table.add_row().cells
    row_cells[0].text = "DOC-202"
    row_cells[1].text = "Word document export ticket"
    row_cells[2].text = "P3"
    row_cells[3].text = "2026-10-05 14:00"

    doc_bytes = io.BytesIO()
    doc.save(doc_bytes)
    doc_bytes.seek(0)

    response = client.post(
        "/api/upload",
        files={
            "file": (
                "weekly_report.docx",
                doc_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["source_filename"] == "weekly_report.docx"
    assert data["file_type"] == "docx"
    assert data["parsed_count"] == 1
    assert data["records"][0]["key"] == "DOC-202"
    assert data["records"][0]["sla_target_days"] == 5.0

    # Validate analytics payload structure
    assert "analytics" in data
    analytics = data["analytics"]
    assert "overdue_distribution" in analytics
    assert all(
        k in analytics["overdue_distribution"]
        for k in ["0-1d", "1-3d", "3-7d", ">7d"]
    )
    assert "severity_distribution" in analytics
    assert all(
        k in analytics["severity_distribution"]
        for k in ["OK", "WARNING", "CRITICAL", "BREACHED"]
    )
    assert "team_rankings" in analytics
    assert isinstance(analytics["team_rankings"], list)


def test_upload_unsupported_extension(client: TestClient) -> None:
    """POST /api/upload rejects unsupported file extensions with 400 Bad Request."""
    fake_pdf = io.BytesIO(b"%PDF-1.4 dummy content")
    response = client.post(
        "/api/upload",
        files={"file": ("export.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file format '.pdf'" in data["detail"]


def test_upload_empty_file(client: TestClient) -> None:
    """POST /api/upload rejects empty 0-byte file with 400 Bad Request."""
    empty_stream = io.BytesIO(b"")
    response = client.post(
        "/api/upload",
        files={"file": ("empty.html", empty_stream, "text/html")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "empty" in data["detail"].lower()


def test_upload_size_limit_exceeded(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /api/upload rejects files exceeding max_upload_size_mb with 413 Payload Too Large."""
    # Temporarily set max upload size to 0 MB to trigger payload limit
    mock_settings = AppSettings(max_upload_size_mb=0)
    monkeypatch.setattr("web.api.routes.get_settings", lambda: mock_settings)

    payload = io.BytesIO(b"<html><body><table><tr><th>Key</th></tr></table></body></html>")
    response = client.post(
        "/api/upload",
        files={"file": ("large_export.html", payload, "text/html")},
    )
    assert response.status_code == 413
    data = response.json()
    assert "File exceeds maximum upload limit" in data["detail"]


def test_upload_html_without_ticket_tables(client: TestClient) -> None:
    """POST /api/upload on HTML with non-ticket tables returns 200 OK with empty records and warnings."""
    html_without_tickets = """
    <html>
    <body>
        <table>
            <tr><th>Product</th><th>Price</th><th>Quantity</th></tr>
            <tr><td>Widget</td><td>$10</td><td>5</td></tr>
        </table>
    </body>
    </html>
    """
    file_bytes = io.BytesIO(html_without_tickets.encode("utf-8"))
    response = client.post(
        "/api/upload",
        files={"file": ("catalog.html", file_bytes, "text/html")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 0
    assert data["parsed_count"] == 0
    assert len(data["warnings"]) > 0


def test_custom_exception_handler_json_format(client: TestClient) -> None:
    """Custom HTTPException handler should return standardized detail and status_code JSON."""
    response = client.get("/api/nonexistent-route")
    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert "detail" in data
