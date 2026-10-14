---
phase: 3
plan: 2
wave: 2
depends_on:
  - "3.1"
files_modified:
  - web/templates/index.html
  - web/static/css/styles.css
  - web/static/js/app.js
  - web/app.py
  - tests/test_web_ui.py
autonomous: true
gap_closure: false

must_haves:
  truths:
    - "GET / renders the modern multi-tab web dashboard HTML template powered by Tailwind CSS CDN"
    - "Tab 1 provides a responsive drag-and-drop file uploader zone supporting .html, .htm, and .docx formats"
    - "Tab 1 displays 4 KPI highlight cards (Total Records, Breached Count & Rate, Avg Overdue Days, Critical Count)"
    - "Tab 2 provides an interactive SLA records data table with search bar, priority filter, severity filter, and sortable headers"
    - "Tab 2 renders status badge pills with color-coded Tailwind styling and an expandable modal for raw_fields inspection"
    - "Tab 3 displays active SLA priority targets, warning limits, and upload configuration fetched from /api/rules"
    - "Static assets (CSS, JS) are served reliably from web/static/ mounted at /static"
    - "Integration tests in tests/test_web_ui.py pass cleanly"
  artifacts:
    - web/templates/index.html
    - web/static/css/styles.css
    - web/static/js/app.js
    - web/app.py
    - tests/test_web_ui.py
---

# Plan 3.2: Modern Multi-Tab Frontend Interface and Drag-and-Drop Dashboard

<objective>
Build a modern, responsive multi-tab web frontend (`web/templates/index.html`, `web/static/js/app.js`, `web/static/css/styles.css`) served directly by FastAPI without any npm/node build requirements.

The interface includes:
- Tab 1: Upload & Overview:
  * Drag-and-drop file uploader zone with visual hover feedback and fallback file picker.
  * Upload progress spinner and file metadata info banner (filename, extraction time, row count).
  * 4 executive KPI summary cards: Total Records, Breached Count & Rate (%), Avg Overdue Days, and Critical Count.
- Tab 2: SLA Records Explorer:
  * Real-time client-side search across ticket key, summary, team, and status.
  * Priority dropdown filter, severity dropdown filter, and "Breached Only" toggle.
  * Sortable column headers (by key, priority, target, elapsed, overdue, severity).
  * Color-coded status badge pills (Compliant/OK, Approaching SLA/Warning, Critical Risk, Breached SLA).
  * Expandable modal / drawer to inspect unmapped columns and `raw_fields` dictionary.
- Tab 3: SLA Rules & Settings:
  * Visual cards detailing active priority target days, warning thresholds, overdue breach criteria, and file upload limits fetched dynamically from `GET /api/rules`.
- Comprehensive web UI tests in `tests/test_web_ui.py` validating root route rendering, static asset delivery, and end-to-end integration.

Purpose: Provide non-technical managers with an intuitive, zero-code drag-and-drop web dashboard to analyze SLA breaches instantly.
Output: `web/templates/index.html`, `web/static/css/styles.css`, `web/static/js/app.js`, updated `web/app.py`, and `tests/test_web_ui.py`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- web/app.py
- web/api/routes.py
- core/models/sla.py
- config/settings.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create multi-tab Jinja2 HTML layout and mount web routes</name>
  <files>
    web/templates/index.html
    web/static/css/styles.css
    web/app.py
  </files>
  <action>
    1. Create `web/templates/index.html`:
       - Responsive HTML5 template importing Tailwind CSS CDN (`https://cdn.tailwindcss.com`) and Inter font.
       - Navigation bar:
         * Application title with shield/clock logo: "SLA Breach Dashboard & Analyzer".
         * Version pill ("v1.0.0") and live system status indicator badge ("System Ready").
         * Tab navigation bar with 3 clickable buttons:
           - Tab 1: "Upload & Overview" (`#tab-btn-upload`)
           - Tab 2: "SLA Records Explorer" (`#tab-btn-records`) with badge counter (`#records-badge`)
           - Tab 3: "SLA Rules & Settings" (`#tab-btn-rules`)
       - Tab 1 Content Panel (`#tab-content-upload`):
         * Drag-and-drop zone (`#drop-zone`):
           - Large dashed drop container with animated cloud upload icon.
           - Text: "Drag & drop Confluence HTML or Word DOCX export here, or click to browse".
           - Hidden input: `<input type="file" id="file-input" accept=".html,.htm,.docx" class="hidden">`.
           - Format badges: HTML (.html, .htm), Word (.docx), Max Size 25 MB.
         * Upload loading spinner (`#upload-spinner`, hidden by default) with status text.
         * File metadata banner (`#file-info-banner`, hidden by default):
           - File name, file size, extraction timestamp, parsed rows count, warning notices.
         * 4 KPI summary cards grid (`#kpi-section`, hidden until file parsed):
           - Card 1: Total Records (Icon, value `#kpi-total-records`, subtitle "Parsed Tickets").
           - Card 2: Breached Records (Icon, value `#kpi-breached-count`, rate badge `#kpi-breach-rate`, subtitle "Overdue Resolution").
           - Card 3: Avg Overdue Days (Icon, value `#kpi-avg-overdue`, subtitle "For Breached Tickets").
           - Card 4: Critical Tickets (Icon, value `#kpi-critical-count`, subtitle "Overdue >= 3 Days").
       - Tab 2 Content Panel (`#tab-content-records`, hidden by default):
         * Filter toolbar:
           - Search input (`#table-search`): text input filtering across key, summary, team, and status.
           - Priority filter dropdown (`#filter-priority`): All, P1, P2, P3, P4.
           - Severity filter dropdown (`#filter-severity`): All, OK, WARNING, CRITICAL, BREACHED.
           - Checkbox toggle (`#filter-breached-only`): "Breached Only".
           - Reset filters button (`#btn-reset-filters`).
           - Counter indicator (`#table-counter`): "Showing X of Y records".
         * Interactive Data Table (`#records-table-container`):
           - Columns: Key, Summary, Team, Priority, Status, Target Days, Elapsed Days, Overdue Days, Severity, Details.
           - Headers styled with hover highlight and sort indicators (`▲/▼`).
           - Empty state placeholder: "No records loaded yet. Drag-and-drop a file in the Upload tab."
         * Raw Fields Modal (`#raw-fields-modal`, hidden by default):
           - Backdrop overlay and modal box displaying ticket key, summary, and formatted JSON/key-value view of unmapped `raw_fields`.
           - Close button and Esc-key handler.
       - Tab 3 Content Panel (`#tab-content-rules`, hidden by default):
         * Priority Target Durations card (`#rules-priorities-list`).
         * Severity Thresholds card (Warning pct, Breached threshold, Critical overdue days).
         * Allowed Ingestion Formats & Upload Limits card.
         * Refresh rules button (`#btn-refresh-rules`).
    2. Create `web/static/css/styles.css`:
       - Dragover active state styling (`.drag-active { border-color: #6366f1; background-color: #eef2ff; }`).
       - Custom scrollbars, modal fade-in animations, and table row hover effects.
    3. Update `web/app.py`:
       - Configure Jinja2 templates: `templates = Jinja2Templates(directory="web/templates")`.
       - Mount static directory at `/static`: `app.mount("/static", StaticFiles(directory="web/static"), name="static")`.
       - Add root route `GET /` returning `templates.TemplateResponse("index.html", {"request": request, "app_name": settings.app_name, "version": settings.app_version})`.

    AVOID: requiring any external npm/Node build steps. USE standard Tailwind CSS CDN script tag.
    AVOID: breaking if static/templates are referenced with relative path issues. Use `Path(__file__).parent / "templates"`.
  </action>
  <verify>
    python -c "from web.app import create_app; from fastapi.testclient import TestClient; client = TestClient(create_app()); res = client.get('/'); assert res.status_code == 200; assert 'SLA Breach Dashboard' in res.text; print('Template and route mounting verified')"
  </verify>
  <done>
    `web/templates/index.html` and `web/static/css/styles.css` are created, and `GET /` serves the multi-tab layout with Tailwind styling and all required DOM elements.
  </done>
</task>

<task type="auto">
  <name>Task 2: Implement client-side JavaScript for drag-and-drop, KPIs, and table explorer</name>
  <files>
    web/static/js/app.js
  </files>
  <action>
    1. Create `web/static/js/app.js` using vanilla modern JavaScript (ES6+):
       - State management:
         * `state = { allRecords: [], filteredRecords: [], currentFile: null, activeRules: null, sortField: 'overdue_days', sortDirection: 'desc' }`.
       - Tab switching:
         * Implement `switchTab(tabName)`: updates tab button visual styles (active border and text color) and toggles visibility of `#tab-content-upload`, `#tab-content-records`, `#tab-content-rules`.
       - Drag-and-drop file upload:
         * Attach event listeners to `#drop-zone`: `dragover`, `dragenter` (adds `.drag-active`), `dragleave`, `drop` (removes `.drag-active`).
         * Handle file drop: extract `event.dataTransfer.files[0]` and trigger `handleFileUpload(file)`.
         * Handle file input click and change event: clicking `#drop-zone` triggers `#file-input.click()`, file selection triggers `handleFileUpload(file)`.
         * Validate file extension against allowed types (`.html`, `.htm`, `.docx`). Display error alert if invalid.
       - Asynchronous upload handler `handleFileUpload(file)`:
         * Show `#upload-spinner` and hide `#file-info-banner`.
         * Create `FormData`, append `file`.
         * Perform `fetch('/api/upload', { method: 'POST', body: formData })`.
         * If response is not ok: parse error detail from response JSON and display alert banner.
         * If response is ok:
           - Store `response.records` into `state.allRecords`.
           - Populate file info banner: filename, size, extraction timestamp, parsed rows count, and any warnings.
           - Call `updateKpis(response.metrics)`.
           - Call `renderTable()`.
           - Update records badge count on Tab 2 button.
           - Switch to Tab 2 or show prompt to view records.
       - KPI card updater `updateKpis(metrics)`:
         * Set `#kpi-total-records`: `metrics.total_records`.
         * Set `#kpi-breached-count`: `metrics.breached_count`.
         * Set `#kpi-breach-rate`: `metrics.breach_rate_pct + '%'`.
         * Set `#kpi-avg-overdue`: `metrics.avg_overdue_days + ' days'`.
         * Set `#kpi-critical-count`: `metrics.by_severity?.CRITICAL || 0`.
         * Unhide `#kpi-section`.
       - Interactive SLA Records Explorer:
         * Filter handler `applyFilters()`:
           - Filters `state.allRecords` based on search term in `#table-search` (case-insensitive search in key, summary, team, status).
           - Filters by priority dropdown `#filter-priority`.
           - Filters by severity dropdown `#filter-severity`.
           - Filters by "Breached Only" checkbox `#filter-breached-only`.
           - Updates `state.filteredRecords`.
         * Sorting handler `applySorting()`:
           - Sorts `state.filteredRecords` by `state.sortField` in `state.sortDirection`.
           - Header click toggles sort direction or changes sort column.
         * Table renderer `renderTable()`:
           - Clears `#records-table-body`.
           - If `state.filteredRecords.length === 0`: render friendly empty state row.
           - For each record, create table row `<tr>`:
             * Key: bold link/text.
             * Summary: truncated summary with title tooltip.
             * Team: team name or "Unassigned".
             * Priority: pill badge (e.g. P1 red, P2 orange, P3 blue).
             * Status: ticket status text.
             * Target Days: target duration formatted to 1 decimal.
             * Elapsed Days: elapsed days formatted to 1 decimal.
             * Overdue Days: overdue days (highlighted red if > 0).
             * Severity: badge pill using color mapping:
               - OK: emerald (`bg-emerald-100 text-emerald-800 border-emerald-300`)
               - WARNING: amber (`bg-amber-100 text-amber-800 border-amber-300`)
               - CRITICAL: orange (`bg-orange-100 text-orange-800 border-orange-300`)
               - BREACHED: rose (`bg-rose-100 text-rose-800 border-rose-300`)
             * Details: "View Raw" button calling `openRawFieldsModal(record)`.
           - Update `#table-counter`: "Showing X of Y records".
       - Raw fields modal:
         * `openRawFieldsModal(record)`: formats `record.raw_fields` as indented JSON syntax into `#raw-fields-json`, sets ticket key header, reveals modal.
         * Close button and backdrop click dismisses modal.
       - Rules & Settings loader:
         * On load, `fetch('/api/rules')`:
           - Populates `#rules-priorities-list` table (Priority vs Target Days).
           - Populates severity criteria (Warning %, Breached days, Critical days).
           - Populates allowed file formats and maximum upload size limit.
    2. Ensure clean modular code structure with event listeners initialized on `DOMContentLoaded`.

    AVOID: third-party client JS libraries (e.g., jQuery, lodash). Write clean, dependency-free vanilla JS.
    AVOID: losing raw_fields attributes when filtering or sorting. Always retain full record objects in memory.
  </action>
  <verify>
    python -c "content = open('web/static/js/app.js', 'r', encoding='utf-8').read(); assert 'handleFileUpload' in content and 'applyFilters' in content and 'renderTable' in content and 'openRawFieldsModal' in content; print('Client JavaScript successfully verified')"
  </verify>
  <done>
    `web/static/js/app.js` is implemented with drag-and-drop handling, async upload, KPI card population, multi-tab switching, client-side search/filter/sort, badge pill styling, raw_fields modal, and settings loader.
  </done>
</task>

<task type="auto">
  <name>Task 3: Implement web UI integration tests and static asset verification</name>
  <files>
    tests/test_web_ui.py
  </files>
  <action>
    1. Create `tests/test_web_ui.py` using `fastapi.testclient.TestClient`:
       - `test_root_route_serves_html`:
         * `client.get("/")` returns 200 OK.
         * `Content-Type` is `text/html; charset=utf-8`.
         * Response body contains app title "SLA Breach Dashboard & Analyzer".
         * Contains key DOM element IDs: `#drop-zone`, `#file-input`, `#tab-content-upload`, `#tab-content-records`, `#tab-content-rules`, `#table-search`, `#raw-fields-modal`.
       - `test_static_assets_serving`:
         * `client.get("/static/js/app.js")` returns 200 OK with `application/javascript` (or matching text/javascript).
         * `client.get("/static/css/styles.css")` returns 200 OK with `text/css`.
         * `client.get("/static/non_existent.file")` returns 404 Not Found.
       - `test_html_template_context_values`:
         * Response body contains rendered app version and title matching `config.settings.get_settings()`.
       - `test_end_to_end_upload_contract_with_frontend_schema`:
         * Upload a valid mock HTML table via `POST /api/upload`.
         * Validate that the JSON keys consumed by `web/static/js/app.js` exist and have expected types:
           - `metrics.total_records` is int
           - `metrics.breached_count` is int
           - `metrics.breach_rate_pct` is float
           - `metrics.avg_overdue_days` is float
           - `records` is a list where each record contains `id`, `key`, `summary`, `status`, `priority`, `sla_target_days`, `elapsed_days`, `overdue_days`, `severity`, and `raw_fields`.
    2. Run tests to confirm 100% pass rate.

    AVOID: brittle substring matches that fail on whitespace changes. Check for semantic markers and key element IDs.
  </action>
  <verify>
    pytest tests/test_web_ui.py -v
  </verify>
  <done>
    `tests/test_web_ui.py` passes cleanly, verifying template rendering, static asset routing, and contract compatibility with client-side JavaScript.
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:
- [ ] Root route `GET /` serves HTML template with Tailwind CSS CDN and tabs
- [ ] Tab 1 drag-and-drop dropzone accepts file drops and triggers async upload
- [ ] 4 KPI highlight cards display correct computed metrics upon upload
- [ ] Tab 2 table explorer filters records in real-time by search text, priority, severity, and breach status
- [ ] Tab 2 sortable headers sort records ascending/descending
- [ ] Raw fields modal opens and displays unmapped columns and ticket data
- [ ] Tab 3 renders active SLA configuration rules from `/api/rules`
- [ ] Static files are served reliably at `/static/css/styles.css` and `/static/js/app.js`
- [ ] All tests in `tests/test_web_ui.py` and the full suite `pytest tests/ -v` pass cleanly
</verification>

<success_criteria>
- [ ] All 3 tasks verified passing
- [ ] Must-haves confirmed
- [ ] Full regression suite passing
</success_criteria>
