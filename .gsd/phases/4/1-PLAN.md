---
phase: 4
plan: 1
wave: 1
depends_on: []
files_modified:
  - core/analytics/__init__.py
  - core/analytics/metrics.py
  - web/api/routes.py
  - web/templates/index.html
  - web/static/js/app.js
  - tests/test_analytics.py
  - tests/test_api.py
  - tests/test_web_ui.py
autonomous: true
gap_closure: false

must_haves:
  truths:
    - "core.analytics.metrics calculates overdue distribution into 4 standard histogram bins (0-1d, 1-3d, 3-7d, >7d)"
    - "core.analytics.metrics aggregates severity breakdown across all 4 severity levels (OK, WARNING, CRITICAL, BREACHED)"
    - "core.analytics.metrics computes team breach rankings sorted by breach count and breach rate percentage"
    - "POST /api/upload returns structured analytics payload alongside metrics and records"
    - "GET / renders Visual Analytics tab with Chart.js CDN script and 3 responsive canvas cards"
    - "Chart.js renders interactive Doughnut chart for severity, Bar chart for overdue distributions, and horizontal Bar chart for team rankings"
    - "Chart instances are cleaned up and destroyed properly prior to re-render to prevent canvas memory leaks"
    - "Unit and UI tests in tests/test_analytics.py, tests/test_api.py, and tests/test_web_ui.py pass cleanly"
  artifacts:
    - core/analytics/metrics.py
    - tests/test_analytics.py
    - web/templates/index.html
    - web/static/js/app.js
---

# Plan 4.1: Visual Analytics Dashboard and Chart Aggregations

<objective>
Implement the backend analytics aggregation engine (`core/analytics/metrics.py`) and modern frontend Visual Analytics tab (`web/templates/index.html`, `web/static/js/app.js`) powered by Chart.js.

The visual analytics engine provides:
- Overdue distribution histogram bins: `0-1d`, `1-3d`, `3-7d`, and `>7d` for overdue tickets.
- Severity distribution breakdown across `OK`, `WARNING`, `CRITICAL`, and `BREACHED`.
- Team breach rankings aggregating total tickets, breached tickets, and breach rate percentages, sorted by breach count descending.
- REST API enhancement in `web/api/routes.py` returning structured `analytics` payload upon file upload.
- Frontend Tab "Visual Analytics" in `web/templates/index.html` with Chart.js CDN integration.
- Three interactive, responsive charts:
  1. Doughnut chart for SLA compliance & severity breakdown (with emerald, amber, orange, and rose colors).
  2. Vertical Bar chart for overdue distribution histogram bins.
  3. Horizontal Bar chart for team breach rankings (breached vs total tickets).
- Proper Chart.js lifecycle management (destroying existing charts before creating new ones on file reload).

Purpose: Empower non-technical managers to immediately visualize SLA breach patterns, overdue bottlenecks, and team rankings through interactive charts.
Output: `core/analytics/metrics.py`, `core/analytics/__init__.py`, `tests/test_analytics.py`, updated `web/api/routes.py`, updated `web/templates/index.html`, and updated `web/static/js/app.js`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- core/models/sla.py
- core/sla/engine.py
- web/api/routes.py
- web/templates/index.html
- web/static/js/app.js
- tests/test_api.py
- tests/test_web_ui.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement backend analytics aggregation engine and unit tests</name>
  <files>
    core/analytics/__init__.py
    core/analytics/metrics.py
    tests/test_analytics.py
  </files>
  <action>
    1. Create `core/analytics/metrics.py`:
       - `compute_overdue_distribution(records: List[SlaRecord]) -> Dict[str, int]`:
         * Iterates over records where `overdue_days is not None and overdue_days > 0`.
         * Groups into 4 discrete bins:
           - `"0-1d"`: `0.0 < overdue_days <= 1.0`
           - `"1-3d"`: `1.0 < overdue_days <= 3.0`
           - `"3-7d"`: `3.0 < overdue_days <= 7.0`
           - `">7d"`: `overdue_days > 7.0`
         * Returns dictionary with keys `["0-1d", "1-3d", "3-7d", ">7d"]`.
       - `compute_severity_distribution(records: List[SlaRecord]) -> Dict[str, int]`:
         * Counts occurrences of each `SeverityLevel` (`OK`, `WARNING`, `CRITICAL`, `BREACHED`).
         * Ensures all 4 keys are present with non-negative integer counts even if 0.
       - `compute_team_rankings(records: List[SlaRecord]) -> List[Dict[str, Any]]`:
         * Aggregates records by team (treats empty, None, or whitespace strings as `"Unassigned"`).
         * For each team computes:
           - `team`: team name
           - `total`: total tickets assigned to team
           - `breached`: count of breached tickets
           - `compliant`: count of non-breached tickets (`total - breached`)
           - `breach_rate_pct`: `round((breached / total) * 100.0, 1)` if `total > 0` else `0.0`
         * Sorts the list of team dictionaries by `breached` descending, then `breach_rate_pct` descending, then `team` ascending.
       - `compute_analytics_payload(records: List[SlaRecord]) -> Dict[str, Any]`:
         * Consolidates:
           - `"overdue_distribution"`: result of `compute_overdue_distribution(records)`
           - `"severity_distribution"`: result of `compute_severity_distribution(records)`
           - `"team_rankings"`: result of `compute_team_rankings(records)`
           - `"summary"`: dictionary with `total_records`, `breached_count`, `breach_rate_pct`, `avg_overdue_days`, `max_overdue_days`.
    2. In `core/analytics/__init__.py`:
       - Export `compute_overdue_distribution`, `compute_severity_distribution`, `compute_team_rankings`, `compute_analytics_payload`.
    3. Create `tests/test_analytics.py`:
       - `test_empty_records_analytics`: verify empty list returns all bins with 0, empty team rankings, and all severity counts at 0.
       - `test_overdue_distribution_bins`: verify exact assignment into `0-1d` (e.g. 0.5d, 1.0d), `1-3d` (e.g. 2.5d, 3.0d), `3-7d` (e.g. 4.5d, 7.0d), and `>7d` (e.g. 8.2d). Verify records with `overdue_days <= 0` or `None` are excluded from overdue bins.
       - `test_severity_distribution`: verify counts for each `SeverityLevel` enum value.
       - `test_team_rankings_aggregation_and_sorting`: verify correct team counts and descending sort order by breached tickets.
       - `test_unassigned_team_fallback`: verify records with `team=None` or empty strings group under `"Unassigned"`.
       - `test_full_analytics_payload`: verify all top-level keys and summary metrics in consolidated payload.

    AVOID: mutating input record objects during aggregation.
    AVOID: division by zero when calculating breach rates for empty team records or empty datasets.
  </action>
  <verify>
    pytest tests/test_analytics.py -v
  </verify>
  <done>
    `core/analytics/metrics.py` implements overdue binning, severity breakdown, and team breach rankings, and `tests/test_analytics.py` passes 100%.
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire analytics payload into upload API route and update API tests</name>
  <files>
    web/api/routes.py
    tests/test_api.py
  </files>
  <action>
    1. In `web/api/routes.py`:
       - Import `compute_analytics_payload` from `core.analytics.metrics`.
       - In `POST /api/upload`:
         * After `engine.process_extraction_result(extraction_result)` and `engine.calculate_summary_metrics(...)`:
         * Generate analytics payload: `analytics = compute_analytics_payload(extraction_result.parsed_records)`.
         * Add `"analytics": analytics` to the response dictionary.
    2. In `tests/test_api.py`:
       - Update `test_upload_html_success` and `test_upload_docx_success`:
         * Assert `"analytics"` key is present in response JSON.
         * Assert `"overdue_distribution"` is present with keys `["0-1d", "1-3d", "3-7d", ">7d"]`.
         * Assert `"severity_distribution"` is present with keys `["OK", "WARNING", "CRITICAL", "BREACHED"]`.
         * Assert `"team_rankings"` is a list containing team summary objects.
    3. Run entire test suite to ensure zero regressions in existing endpoints.

    AVOID: altering the schema of existing keys (`source_filename`, `metrics`, `records`). Add `"analytics"` as an additive field.
  </action>
  <verify>
    pytest tests/test_api.py -v
  </verify>
  <done>
    `POST /api/upload` returns the comprehensive analytics payload and all API tests pass.
  </done>
</task>

<task type="auto">
  <name>Task 3: Implement Visual Analytics tab and Chart.js dashboards in frontend</name>
  <files>
    web/templates/index.html
    web/static/js/app.js
    tests/test_web_ui.py
  </files>
  <action>
    1. Update `web/templates/index.html`:
       - Add Chart.js CDN script in `<head>`: `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>`.
       - In Top Navigation Bar, add Tab button between "SLA Records Explorer" and "SLA Rules & Settings":
         ```html
         <button id="tab-btn-analytics" type="button" class="tab-button inline-flex items-center px-4 py-2.5 border-b-2 border-transparent font-medium text-sm text-slate-600 hover:text-slate-900 hover:border-slate-300 transition-colors">
             <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
             </svg>
             Visual Analytics
         </button>
         ```
       - Add Tab Content Panel `<section id="tab-content-analytics" class="hidden space-y-6">`:
         * Empty State Card (`#analytics-empty-state`):
           - Centered illustration and prompt: "No visual analytics available. Drag-and-drop a Confluence HTML or Word DOCX export file in the Upload tab to generate visual charts."
         * Analytics Dashboard Grid (`#analytics-dashboard`, hidden until file uploaded):
           - Subheader banner showing loaded file name and quick badge stats.
           - Grid container: `grid grid-cols-1 lg:grid-cols-2 gap-6`:
             1. Chart Card 1: SLA Compliance & Severity Breakdown:
                - Header with icon and title.
                - Canvas: `<div class="relative h-64 flex items-center justify-center"><canvas id="chart-severity"></canvas></div>`.
             2. Chart Card 2: Overdue Distribution Histogram:
                - Header with icon and title (bins: 0-1d, 1-3d, 3-7d, >7d).
                - Canvas: `<div class="relative h-64"><canvas id="chart-overdue"></canvas></div>`.
             3. Chart Card 3 (full width `lg:col-span-2`): Team Breach Rankings:
                - Header with icon and title (ranked by breached tickets).
                - Canvas: `<div class="relative h-72"><canvas id="chart-teams"></canvas></div>`.
    2. Update `web/static/js/app.js`:
       - Include `'analytics'` in `initTabNavigation()` and `switchTab(tabName)`:
         * Add event listener for `#tab-btn-analytics`.
         * Add `'analytics'` to the `tabs` array in `switchTab`.
         * When switching to `'analytics'`, call `renderAllCharts()` and trigger `chart.resize()` on existing instances so canvas displays with correct dimensions.
       - Maintain state:
         * `state.analytics = null;`
         * `state.charts = { severity: null, overdue: null, teams: null };`
       - In `handleFileUpload(file)`:
         * If `data.analytics`:
           - Store `state.analytics = data.analytics;`
           - Show `#analytics-dashboard` and hide `#analytics-empty-state`.
           - Call `renderAllCharts()`.
       - Implement chart rendering functions:
         * `destroyCharts()`: loops through `state.charts` and calls `.destroy()` on any active Chart.js instance to prevent canvas memory leaks.
         * `renderSeverityChart(severityData)`:
           - Doughnut chart on `#chart-severity`.
           - Labels: `['Compliant (OK)', 'Approaching (WARNING)', 'Critical Risk', 'Breached SLA']`.
           - Colors: Emerald (`#10b981`), Amber (`#f59e0b`), Orange (`#f97316`), Rose (`#f43f5e`).
           - Cutout: `'65%'`, tooltips with percentages and counts.
         * `renderOverdueChart(overdueData)`:
           - Vertical bar chart on `#chart-overdue`.
           - Labels: `['0-1 Days', '1-3 Days', '3-7 Days', '> 7 Days']`.
           - Background colors corresponding to urgency (Indigo `#6366f1`, Amber `#f59e0b`, Orange `#f97316`, Rose `#f43f5e`).
           - Y-axis integer steps.
         * `renderTeamRankingsChart(teamList)`:
           - Horizontal bar chart (`indexAxis: 'y'`) on `#chart-teams`.
           - Labels: team names.
           - Datasets:
             - Dataset 1: "Breached Tickets" (Rose `#f43f5e`).
             - Dataset 2: "Compliant Tickets" (Emerald `#10b981` or Slate `#cbd5e1`).
       - Ensure `renderAllCharts()` handles edge cases (e.g. empty team list, all zeros) gracefully without throwing JavaScript errors.
    3. Update `tests/test_web_ui.py`:
       - Verify `GET /` serves HTML containing `cdn.jsdelivr.net/npm/chart.js`.
       - Verify `#tab-btn-analytics`, `#tab-content-analytics`, `#chart-severity`, `#chart-overdue`, and `#chart-teams` exist in DOM.
       - Verify mock upload response contract includes `analytics` object.

    AVOID: creating Chart.js instances without destroying previous instances when a new file is uploaded.
    AVOID: chart sizing distortion by using fixed height responsive wrappers (`relative h-64`) with `responsive: true, maintainAspectRatio: false`.
  </action>
  <verify>
    pytest tests/test_web_ui.py tests/test_analytics.py -v
  </verify>
  <done>
    Visual Analytics tab with Chart.js CDN renders three responsive charts (severity doughnut, overdue histogram, team rankings) with proper lifecycle cleanup and passing UI tests.
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:
- [ ] `core.analytics.metrics` computes 4 overdue histogram bins (`0-1d`, `1-3d`, `3-7d`, `>7d`)
- [ ] `core.analytics.metrics` aggregates severity distribution across all levels
- [ ] `core.analytics.metrics` calculates team breach rankings sorted descending by breach count
- [ ] `POST /api/upload` returns the `analytics` dictionary containing all aggregated chart metrics
- [ ] `GET /` includes Chart.js CDN and renders `#tab-content-analytics` with three canvas elements
- [ ] Switching to Visual Analytics tab displays responsive charts with appropriate color coding
- [ ] Re-uploading files destroys previous Chart.js instances and recreates clean charts without errors
- [ ] All unit and UI tests in `tests/test_analytics.py`, `tests/test_api.py`, and `tests/test_web_ui.py` pass cleanly
</verification>

<success_criteria>
- [ ] All 3 tasks verified passing
- [ ] Must-haves confirmed
- [ ] Zero regressions in existing test suite
</success_criteria>
