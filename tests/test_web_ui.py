"""Integration tests for web dashboard UI, template rendering, and static assets."""

import io
from fastapi.testclient import TestClient
import pytest

from config.settings import get_settings
from web.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a FastAPI TestClient instance."""
    app = create_app()
    return TestClient(app)


def test_root_serves_react_build(client: TestClient) -> None:
    """Validate that GET / serves the compiled React frontend when dist/index.html exists."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Dashboard & Analyzer" in response.text
    assert '<div id="root"' in response.text


def test_root_route_serves_html(client: TestClient) -> None:
    """Validate that GET /?view=template renders HTML template with 200 OK and expected DOM elements."""
    response = client.get("/?view=template")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    body = response.text
    # Check title / branding
    assert "SLA Breach Dashboard" in body
    assert "Confluence &amp; Word Export Ticket Ingestion Engine" in body

    # Verify Chart.js script is included
    assert "cdn.jsdelivr.net/npm/chart.js" in body

    # Verify presence of essential UI container IDs
    required_ids = [
        "drop-zone",
        "file-input",
        "upload-spinner",
        "file-info-banner",
        "kpi-section",
        "tab-btn-upload",
        "tab-btn-records",
        "tab-btn-analytics",
        "tab-btn-rules",
        "tab-content-upload",
        "tab-content-records",
        "tab-content-analytics",
        "analytics-empty-state",
        "analytics-dashboard",
        "chart-severity",
        "chart-overdue",
        "chart-teams",
        "tab-content-rules",
        "table-search",
        "filter-priority",
        "filter-severity",
        "filter-breached-only",
        "records-table-container",
        "records-table-body",
        "raw-fields-modal",
        "raw-fields-json",
        "rules-priorities-list",
    ]

    for element_id in required_ids:
        assert f'id="{element_id}"' in body, f"Expected DOM element #{element_id} in template"


def test_static_assets_serving(client: TestClient) -> None:
    """Verify that static assets (JavaScript and CSS) are served reliably at /static."""
    # Test JavaScript bundle
    res_js = client.get("/static/js/app.js")
    assert res_js.status_code == 200
    assert any(
        mime in res_js.headers["content-type"]
        for mime in ["application/javascript", "text/javascript"]
    )
    assert "handleFileUpload" in res_js.text
    assert "applyFilters" in res_js.text
    assert "renderTable" in res_js.text
    assert "openRawFieldsModal" in res_js.text
    assert "renderAllCharts" in res_js.text
    assert "destroyCharts" in res_js.text
    assert "renderSeverityChart" in res_js.text
    assert "renderOverdueChart" in res_js.text
    assert "renderTeamRankingsChart" in res_js.text

    # Test CSS bundle
    res_css = client.get("/static/css/styles.css")
    assert res_css.status_code == 200
    assert "text/css" in res_css.headers["content-type"]
    assert ".drag-active" in res_css.text

    # Test non-existent static asset returns 404
    res_missing = client.get("/static/non_existent.file")
    assert res_missing.status_code == 404


def test_html_template_context_values(client: TestClient) -> None:
    """Verify that template context dynamically renders application settings values."""
    settings = get_settings()
    response = client.get("/?view=template")
    assert response.status_code == 200

    body = response.text
    assert f"v{settings.app_version}" in body
    assert settings.app_name in body


def test_end_to_end_upload_contract_with_frontend_schema(client: TestClient) -> None:
    """Verify that /api/upload returns the schema expected by the frontend JavaScript state and table."""
    sample_html = """
    <html>
    <body>
        <table>
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Summary</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Resolved</th>
                    <th>Team</th>
                    <th>Custom Field</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>INFRA-991</td>
                    <td>Database failover outage</td>
                    <td>P1</td>
                    <td>Closed</td>
                    <td>2026-01-01</td>
                    <td>2026-01-05</td>
                    <td>Platform Ops</td>
                    <td>Custom Val A</td>
                </tr>
                <tr>
                    <td>APP-402</td>
                    <td>Update button padding</td>
                    <td>P3</td>
                    <td>In Progress</td>
                    <td>2026-01-01</td>
                    <td></td>
                    <td>UI Team</td>
                    <td>Custom Val B</td>
                </tr>
            </tbody>
        </table>
    </body>
    </html>
    """

    file_bytes = io.BytesIO(sample_html.encode("utf-8"))
    response = client.post(
        "/api/upload",
        files={"file": ("tickets.html", file_bytes, "text/html")},
    )

    assert response.status_code == 200
    data = response.json()

    # Metrics schema consumed by updateKpis() in app.js
    metrics = data.get("metrics")
    assert metrics is not None
    assert isinstance(metrics.get("total_records"), int)
    assert metrics["total_records"] == 2
    assert isinstance(metrics.get("breached_count"), int)
    assert isinstance(metrics.get("breach_rate_pct"), (int, float))
    assert isinstance(metrics.get("avg_overdue_days"), (int, float))
    assert isinstance(metrics.get("by_severity"), dict)

    # Analytics schema consumed by renderAllCharts() in app.js
    analytics = data.get("analytics")
    assert analytics is not None
    assert "overdue_distribution" in analytics
    assert "severity_distribution" in analytics
    assert "team_rankings" in analytics
    assert "summary" in analytics
    assert isinstance(analytics["team_rankings"], list)

    # Records schema consumed by renderTable() and openRawFieldsModal()
    records = data.get("records")
    assert isinstance(records, list)
    assert len(records) == 2

    for rec in records:
        assert "id" in rec
        assert "key" in rec
        assert "summary" in rec
        assert "status" in rec
        assert "priority" in rec
        assert "sla_target_days" in rec
        assert "elapsed_days" in rec
        assert "overdue_days" in rec
        assert "severity" in rec
        assert "raw_fields" in rec
        assert isinstance(rec["raw_fields"], dict)

    # Verify custom unmapped field is preserved in raw_fields
    infra_rec = next(r for r in records if r["key"] == "INFRA-991")
    assert infra_rec["team"] == "Platform Ops"
    assert "Custom Field" in infra_rec["raw_fields"] or "custom field" in infra_rec["raw_fields"]


def test_rules_endpoint_contract_with_frontend(client: TestClient) -> None:
    """Verify that /api/rules provides data consumed by loadRules() in app.js."""
    response = client.get("/api/rules")
    assert response.status_code == 200
    rules = response.json()

    # Priorities target days
    assert "sla_thresholds" in rules
    assert (
        "priority_targets_days" in rules["sla_thresholds"]
        or "priority_target_days" in rules["sla_thresholds"]
    )
    targets = (
        rules["sla_thresholds"].get("priority_targets_days")
        or rules["sla_thresholds"].get("priority_target_days")
    )
    assert "P1" in targets
    assert "P2" in targets

    # Severity rules
    assert "severity_rules" in rules
    s_rules = rules["severity_rules"]
    assert "warning_threshold_pct" in s_rules
    assert (
        "breached_threshold_days" in s_rules
        or "breached_overdue_days_threshold" in s_rules
    )
    assert (
        "critical_overdue_days" in s_rules
        or "critical_overdue_days_threshold" in s_rules
    )

    # Constraints
    assert "allowed_extensions" in rules
    assert ".html" in rules["allowed_extensions"]
    assert ".docx" in rules["allowed_extensions"]
    assert "max_upload_size_mb" in rules


def test_kpi_section_positioned_above_upload_drop_zone(client: TestClient) -> None:
    """Verify that the 4 KPI cards grid is rendered in the DOM above the upload drop zone."""
    response = client.get("/?view=template")
    assert response.status_code == 200
    body = response.text

    kpi_idx = body.find('id="kpi-section"')
    drop_idx = body.find('id="drop-zone"')

    assert kpi_idx != -1, "Expected #kpi-section in DOM"
    assert drop_idx != -1, "Expected #drop-zone in DOM"
    assert kpi_idx < drop_idx, (
        f"Expected #kpi-section (index {kpi_idx}) to appear before #drop-zone (index {drop_idx}) in DOM"
    )

