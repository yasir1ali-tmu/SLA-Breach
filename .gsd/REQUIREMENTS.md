---
milestone: v1.0
updated: 2026-10-14T02:39:30Z
---

# Requirements

## Overview
Functional and non-functional requirements derived from `SPEC.md` for traceability and coverage tracking.

---

## Functional Requirements

| ID | Requirement | Source | Phase | Status |
|----|-------------|--------|-------|--------|
| REQ-01 | Modular project structure with `config/`, `core/`, and `web/` packages | SPEC Goal 1 | 1 | Complete |
| REQ-02 | Pydantic data models for parsed records, SLA status, and metric aggregates | SPEC Goal 1 | 1 | Complete |
| REQ-03 | HTML & Confluence table extraction module with flexible column mapping | SPEC Goal 2 | 2 | Pending |
| REQ-04 | Word (.docx) document table extraction module | SPEC Goal 2 | 2 | Pending |
| REQ-05 | SLA calculation engine (duration, overdue days/hours, severity categorizer) | SPEC Goal 3 | 2 | Pending |
| REQ-06 | FastAPI REST endpoints for file upload, validation, and analytics querying | SPEC Goal 4 | 3 | Pending |
| REQ-07 | Multi-tab modern web UI (Upload/Overview, Breach Records, Visual Dashboards) | SPEC Goal 4 | 3 | Pending |
| REQ-08 | Drag-and-drop file uploader with progress and status feedback | SPEC Goal 4 | 3 | Pending |
| REQ-09 | Interactive visual dashboard charts (severity breakdown, overdue distribution) | SPEC Goal 4 | 4 | Pending |
| REQ-10 | Configurable SLA thresholds & rules loaded from YAML/JSON config | SPEC Goal 1 | 1 | Complete |

---

## Non-Functional Requirements

| ID | Requirement | Category | Phase | Status |
|----|-------------|----------|-------|--------|
| NFR-01 | File processing time < 3 seconds for standard export files (< 5MB) | Performance | 2 | Pending |
| NFR-02 | Zero-npm runtime: Frontend delivered via FastAPI static files / CDN | Usability / Ops | 3 | Pending |
| NFR-03 | Comprehensive docstrings and type annotations across all core functions | Maintainability | All | In Progress |
| NFR-04 | Resilient error handling with clear human-readable messages for invalid files | Reliability | 3 | Pending |

---

## Traceability Matrix

| Requirement | Plans | Tests | Status |
|-------------|-------|-------|--------|
| REQ-01 | 1.1 | Package imports verification | Complete |
| REQ-02 | 1.1 | `tests/test_models.py` (7 tests) | Complete |
| REQ-10 | 1.2 | `tests/test_config.py` (10 tests) | Complete |
| REQ-03 | 2.1 | HTML parser unit tests | Pending |
| REQ-04 | 2.1 | DOCX parser unit tests | Pending |
| REQ-05 | 2.2 | SLA engine computation unit tests | Pending |
| REQ-06 | 3.1 | FastAPI endpoint tests | Pending |
| REQ-07 | 3.2 | Web UI navigation & rendering test | Pending |
| REQ-08 | 3.2 | Upload drag-and-drop integration test | Pending |
| REQ-09 | 4.1 | Dashboard metrics & chart rendering test | Pending |
| NFR-01 | 2.2 | Ingestion benchmark | Pending |
| NFR-02 | 3.2 | Static assets verification | Pending |
| NFR-03 | All | Code review & lint verification | In Progress |
| NFR-04 | 3.1 | Error boundary tests | Pending |
