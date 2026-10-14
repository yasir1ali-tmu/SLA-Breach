---
phase: 4
plan: 2
wave: 2
depends_on:
  - "4.1"
files_modified:
  - run.py
  - tests/test_runner.py
  - tests/test_e2e.py
  - README.md
autonomous: true
gap_closure: false

must_haves:
  truths:
    - "run.py provides a single-command entry point to launch the uvicorn ASGI server with configurable host, port, reload, and browser auto-open"
    - "run.py --help outputs CLI arguments and default values matching application settings"
    - "tests/test_runner.py validates CLI argument parsing, defaults, and banner output"
    - "tests/test_e2e.py validates the complete end-to-end flow from multi-format file ingestion (HTML, DOCX) through SLA calculations and analytics chart payloads"
    - "tests/test_e2e.py verifies error resiliency for corrupted, empty, or unsupported files"
    - "README.md delivers an executive architecture overview, one-command quick start, non-technical manager runbook, and REST API documentation"
    - "All project tests pass cleanly with zero failures"
  artifacts:
    - run.py
    - tests/test_runner.py
    - tests/test_e2e.py
    - README.md
---

# Plan 4.2: End-to-End Validation, Local Server Launcher, and Runbook Documentation

<objective>
Implement the single-command server launcher (`run.py`), comprehensive end-to-end integration test suite (`tests/test_e2e.py`), and executive README with an operational runbook for non-technical managers (`README.md`).

The deliverables include:
- Single-command local launcher `run.py` integrating with `config.settings.get_settings()`, CLI argument parsing via `argparse` (`--host`, `--port`, `--reload`, `--open-browser`), formatted startup ASCII banner, and browser launching.
- Unit tests in `tests/test_runner.py` verifying CLI argument parsing and default values.
- Comprehensive end-to-end test suite `tests/test_e2e.py` validating the full pipeline:
  * Multi-priority HTML export parsing, duration calculations, overdue bins (`0-1d`, `1-3d`, `3-7d`, `>7d`), and team rankings.
  * Word (.docx) export table ingestion, parsing, and SLA metric computation.
  * Web UI route rendering, Chart.js asset availability, and API contract matching.
  * Edge cases, empty files, corrupted markup, and oversized upload rejection.
- Polished, comprehensive `README.md` containing architecture diagrams, 1-command quick start guide, an operational step-by-step runbook for non-technical managers, REST API documentation, and developer testing guidelines.

Purpose: Provide an effortless zero-configuration launch experience, complete automated validation across the entire system, and crystal-clear documentation for operational managers and engineers.
Output: `run.py`, `tests/test_runner.py`, `tests/test_e2e.py`, and `README.md`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- config/settings.py
- web/app.py
- web/api/routes.py
- core/parsers/html_parser.py
- core/parsers/docx_parser.py
- core/sla/engine.py
- core/analytics/metrics.py
- web/templates/index.html
- web/static/js/app.js
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement single-command application launcher and runner test suite</name>
  <files>
    run.py
    tests/test_runner.py
  </files>
  <action>
    1. Create `run.py`:
       - Import `argparse`, `sys`, `threading`, `time`, `webbrowser`, and `uvicorn`.
       - Import `get_settings` from `config.settings`.
       - Define `parse_args(args=None)`:
         * `--host`: default from `settings.host` (`"127.0.0.1"`).
         * `--port`: int, default from `settings.port` (`8000`).
         * `--reload`: action `"store_true"` (default `settings.debug`).
         * `--no-reload`: action `"store_true"`.
         * `--open-browser`: action `"store_true"`, default `False`.
         * `--log-level`: default `"info"`.
       - Define `print_startup_banner(host: str, port: int)`:
         * Prints formatted ASCII banner with application title, version, local dashboard URL (`http://{host}:{port}`), API Swagger docs (`http://{host}:{port}/api/docs`), and instructions to stop (`Press CTRL+C to stop the server`).
       - Define `open_browser_delayed(url: str, delay: float = 1.0)`:
         * Daemon thread target executing `time.sleep(delay)` then `webbrowser.open(url)`.
       - Define `main()`:
         * Parses CLI arguments.
         * Resolves reload setting (`False` if `--no-reload` else `--reload` or `settings.debug`).
         * If `--open-browser`: starts delayed browser thread.
         * Prints startup banner.
         * Runs `uvicorn.run("web.app:create_app", factory=True, host=args.host, port=args.port, reload=reload_flag, log_level=args.log_level)`.
       - Add `if __name__ == "__main__": main()`.
    2. Create `tests/test_runner.py`:
       - Test `parse_args` default values match `config.settings.get_settings()`.
       - Test `parse_args` with custom flags (`--host 0.0.0.0 --port 9090 --reload --open-browser`).
       - Test `print_startup_banner` contains expected URLs and app title.

    AVOID: blocking the main thread before starting uvicorn when opening the browser. Use a background daemon thread.
    AVOID: hardcoding host and port. Always bind defaults to `config.settings.get_settings()`.
  </action>
  <verify>
    pytest tests/test_runner.py -v
  </verify>
  <done>
    `run.py` provides a single-command server launcher with CLI argument overrides, and `tests/test_runner.py` validates parsing and banner display.
  </done>
</task>

<task type="auto">
  <name>Task 2: Implement comprehensive end-to-end integration test suite</name>
  <files>
    tests/test_e2e.py
  </files>
  <action>
    1. Create `tests/test_e2e.py` using `fastapi.testclient.TestClient` with `create_app()`:
       - Scenario 1: Comprehensive HTML Ingestion & SLA Calculation E2E:
         * Construct realistic Confluence/HTML table containing 10+ tickets:
           - Priorities: P1, P2, P3, P4.
           - Teams: "Platform", "Frontend", "Backend", "DevOps", and unassigned.
           - Mix of resolved tickets (some compliant, some overdue) and open tickets (created recently vs long ago).
           - Tickets spanning overdue bins: `0-1d`, `1-3d`, `3-7d`, and `>7d`.
         * Send `POST /api/upload` as multipart form.
         * Verify 200 OK.
         * Assert all records parsed and calculated (`elapsed_days`, `overdue_days`, `severity`).
         * Assert `analytics` payload:
           - `analytics["overdue_distribution"]["0-1d"]` >= 1
           - `analytics["overdue_distribution"]["1-3d"]` >= 1
           - `analytics["overdue_distribution"]["3-7d"]` >= 1
           - `analytics["overdue_distribution"][">7d"]` >= 1
           - Sum of overdue bins equals `metrics["breached_count"]`.
           - `analytics["severity_distribution"]` counts sum to total records.
           - `analytics["team_rankings"]` has teams ordered by breached count descending.
       - Scenario 2: Comprehensive DOCX Ingestion E2E:
         * Construct in-memory Word document using `docx.Document()`.
         * Add table with standard ticket columns (Key, Summary, Priority, Status, Created Date, Resolved Date, Team).
         * Populate multiple rows with diverse dates and priorities.
         * Send `POST /api/upload`.
         * Assert 200 OK, verify records parsed and metrics/analytics accurately computed.
       - Scenario 3: Full Web UI Lifecycle Contract:
         * `client.get("/")` returns 200 OK.
         * Assert presence of all 4 tabs: `#tab-btn-upload`, `#tab-btn-records`, `#tab-btn-analytics`, `#tab-btn-rules`.
         * Assert presence of Chart.js CDN script and all 3 chart canvases: `#chart-severity`, `#chart-overdue`, `#chart-teams`.
         * `client.get("/api/rules")` returns 200 OK with SLA thresholds and priority mappings.
         * `client.get("/static/js/app.js")` and `client.get("/static/css/styles.css")` return 200 OK.
       - Scenario 4: Error Resiliency and Edge Cases:
         * Empty file (0 bytes) returns 400 Bad Request.
         * Unsupported format (`.pdf`, `.xlsx`) returns 400 Bad Request.
         * HTML with no ticket table returns 200 OK with `total_rows == 0` and descriptive warning.
         * Malformed HTML markup still parses safely without 500 error.
    2. Run all tests to confirm 100% pass rate.

    AVOID: writing temporary files to the filesystem. Use `io.BytesIO` for in-memory multipart uploads.
    AVOID: mocking internal parsers or SlaEngine in E2E tests. Test real integration through the HTTP interface.
  </action>
  <verify>
    pytest tests/test_e2e.py -v
  </verify>
  <done>
    `tests/test_e2e.py` validates the complete system end-to-end across parsers, calculation engine, analytics aggregations, web API, and UI templates.
  </done>
</task>

<task type="auto">
  <name>Task 3: Author comprehensive README with architecture overview and manager runbook</name>
  <files>
    README.md
  </files>
  <action>
    1. Create `README.md` with polished Markdown documentation:
       - Header & Project Description:
         * Application Title: SLA Breach Dashboard & Analyzer.
         * Mission: Clean, modular Python system replacing 1600+ line monolithic scripts to parse Confluence HTML and Word DOCX ticket tables, calculate SLA compliance, and provide interactive dashboards.
       - Architecture Overview:
         * Mermaid diagram or ASCII diagram illustrating data flow:
           Input Files (HTML / DOCX) -> Parser Layer (`core/parsers/`) -> SLA Calculation Engine (`core/sla/`) -> Analytics Aggregator (`core/analytics/`) -> FastAPI REST API (`web/api/`) -> Modern Multi-Tab Dashboard (HTML / Tailwind CSS / Chart.js).
         * Modular directory tree explaining responsibilities of `config/`, `core/models/`, `core/parsers/`, `core/sla/`, `core/analytics/`, and `web/`.
       - Quick Start (Single-Command Setup):
         * Step 1: `python -m venv venv` and activate.
         * Step 2: `pip install -r requirements.txt`.
         * Step 3: `python run.py` (or `python run.py --open-browser`).
         * Access interface at `http://127.0.0.1:8000`.
       - Operational Runbook for Non-Technical Managers:
         * Step-by-step workflow guide with zero command-line requirements after starting:
           1. Ingesting Exports: How to export tables from Confluence (Export to HTML) or Word, and drag-and-drop into Tab 1.
           2. Reading Overview KPIs: Interpreting Total Records, Breached Count & Rate, Avg Overdue Days, and Critical Count.
           3. Exploring Records in Tab 2: Searching by key or text, filtering by priority (P1-P4) or severity, sorting columns, and opening the "View Raw" modal to inspect unmapped columns.
           4. Analyzing Visual Dashboards in Tab 3:
              - Severity Breakdown (Compliant vs Breached vs Risk).
              - Overdue Distribution Histogram (identifying tickets overdue by 0-1d, 1-3d, 3-7d, >7d).
              - Team Breach Leaderboard (identifying teams with highest breach volumes).
           5. Modifying SLA Rules: How to adjust target days and thresholds in `config/default_sla_rules.yaml`.
       - REST API Reference:
         * `GET /api/health`: Service health and timestamp.
         * `GET /api/rules`: Active SLA configuration and upload constraints.
         * `POST /api/upload`: Multipart file upload returning records, summary KPIs, and analytics.
         * Interactive Swagger docs link (`/api/docs`).
       - Verification & Testing:
         * Running full test suite: `pytest tests/ -v`.
         * Architecture compliance and type validation.

    AVOID: assuming non-technical managers understand technical jargon without context. Provide clear, practical steps for day-to-day operations.
    AVOID: omitting API documentation or config file customization details.
  </action>
  <verify>
    python -c "content = open('README.md', 'r', encoding='utf-8').read(); assert 'SLA Breach Dashboard' in content and 'run.py' in content and 'Runbook' in content and '/api/upload' in content; print('README.md successfully verified')"
  </verify>
  <done>
    `README.md` provides an operational runbook for managers, architecture overview, quick-start guide, and REST API documentation.
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:
- [ ] `run.py` launches the application locally with a single command and supports `--host`, `--port`, `--reload`, and `--open-browser`
- [ ] `tests/test_runner.py` validates CLI argument parsing and default values
- [ ] `tests/test_e2e.py` validates end-to-end HTML and DOCX file processing, calculations, analytics payloads, and error resiliency
- [ ] `README.md` provides complete architecture overview, 1-command quick start, non-technical manager runbook, and REST API docs
- [ ] Entire test suite `pytest tests/ -v` passes cleanly with zero failures or regressions
</verification>

<success_criteria>
- [ ] All 3 tasks verified passing
- [ ] Must-haves confirmed
- [ ] 100% test pass rate across unit, API, and E2E suites
</success_criteria>
