---
milestone: v1.0
version: 1.0.0
updated: 2026-10-14T02:39:00Z
---

# Roadmap

> **Current Phase:** 2 - Core Parsing & SLA Calculation Engine
> **Status:** Ready for Planning

## Must-Haves (from SPEC)

- [x] Clean modular architecture with `config/`, `core/`, and `web/` packages.
- [ ] Confluence/HTML and DOCX table extraction parsers.
- [ ] Core SLA calculation engine (durations, overdue days/hours, breach threshold detection).
- [ ] FastAPI web application with drag-and-drop file upload.
- [ ] Interactive multi-tab web dashboard with search, filter, and visual metric charts.
- [x] Human-readable docstrings and strict typing throughout.

---

## Phases

### Phase 1: Project Foundation & Architecture Setup
**Status:** ✅ Complete
**Objective:** Establish modular folder scaffolding (`config/`, `core/`, `web/`), configuration management, dependencies, and core Pydantic data models.
**Requirements:** REQ-01, REQ-02, REQ-10

**Plans:**
- [x] Plan 1.1: Project scaffolding, environment dependencies (`requirements.txt`), and core data models (`core/models/`).
- [x] Plan 1.2: Configuration system (`config/`) for default SLA thresholds, field mappings, and app settings.

---

### Phase 2: Core Parsing & SLA Calculation Engine
**Status:** ⬜ Not Started
**Objective:** Implement modular parsers for Confluence/HTML and Word (.docx) table extraction, and build the core SLA breach and overdue calculation engine.
**Depends on:** Phase 1
**Requirements:** REQ-03, REQ-04, REQ-05, NFR-01

**Plans:**
- [ ] Plan 2.1: Table extraction modules for Confluence/HTML (`core/parsers/html_parser.py`) and DOCX (`core/parsers/docx_parser.py`).
- [ ] Plan 2.2: SLA breach calculation engine (`core/sla/engine.py`), duration/overdue calculators, and severity categorizer.

---

### Phase 3: Web Application & REST API (FastAPI + Drag-and-Drop)
**Status:** ⬜ Not Started
**Objective:** Implement the FastAPI application backend endpoints and modern multi-tab frontend interface with a drag-and-drop file uploader and interactive breach tables.
**Depends on:** Phase 2
**Requirements:** REQ-06, REQ-07, REQ-08, NFR-02, NFR-04

**Plans:**
- [ ] Plan 3.1: FastAPI server, API routes for file upload, validation, parsing, and SLA breach querying (`web/api/`).
- [ ] Plan 3.2: Multi-tab responsive web UI (HTML/Tailwind CSS/JS) featuring drag-and-drop file uploader and interactive data table (`web/static/`, `web/templates/`).

---

### Phase 4: Visual Dashboards, Analytics & Polish
**Status:** ⬜ Not Started
**Objective:** Add visual interactive dashboards (Chart.js charts for breach severity, overdue histograms, team breakdown), end-to-end integration testing, and operational runbook.
**Depends on:** Phase 3
**Requirements:** REQ-09, NFR-03

**Plans:**
- [ ] Plan 4.1: Interactive dashboard charts, KPI summary widgets, and metrics aggregators (`core/analytics/`).
- [ ] Plan 4.2: End-to-end testing with sample datasets, runbook/documentation, and final code verification.

---

## Progress Summary

| Phase | Status | Plans | Complete |
|-------|--------|-------|----------|
| 1 | ✅ | 2/2 | 100% |
| 2 | ⬜ | 0/2 | — |
| 3 | ⬜ | 0/2 | — |
| 4 | ⬜ | 0/2 | — |

---

## Timeline

| Phase | Started | Completed | Duration |
|-------|---------|-----------|----------|
| 1 | 2026-10-13 | 2026-10-13 | ~15m |
| 2 | — | — | — |
| 3 | — | — | — |
| 4 | — | — | — |
