# SPEC.md — Project Specification

> **Status**: `FINALIZED`
>
> ⚠️ **Planning Lock**: Requirements and scope are established. Changes must be recorded in DECISIONS.md.

---

## Vision
Transform a 1611-line monolithic Python processing script into a clean, modular, maintainable Python system with a FastAPI backend and a modern multi-tab web dashboard. The application enables non-technical managers to drag-and-drop Confluence HTML and Word (.docx) export files, extract tabular data, accurately compute SLA breaches and overdue metrics, and explore interactive visual analytics dashboards without touching any code or command-line tools.

---

## Goals
1. **Modular Code Architecture**: Deconstruct the legacy monolith into clean, single-responsibility modules (`config/`, `core/parsers/`, `core/sla/`, `core/models/`, `web/`) with comprehensive type hints, human-readable docstrings, and robust error handling.
2. **Multi-Format Ingestion**: Ingest and parse tables from Confluence/HTML exports and Word (`.docx`) documents with resilient column detection and data normalization.
3. **Robust SLA Calculation Engine**: Accurately calculate durations, elapsed times, overdue days/hours, and breach severity ratings according to configurable SLA rules.
4. **Intuitive Multi-Tab Web Dashboard**: Provide a modern, clean web interface (FastAPI + HTML/Tailwind CSS + Chart.js) featuring:
   - Drag-and-drop file upload zone.
   - Interactive, searchable, and filterable data tables displaying SLA breached records.
   - Visual KPI dashboard (charts, breach severity breakdown, overdue distribution histograms).
5. **Operational Simplicity**: Ensure the application can be launched locally with a single command and used effortlessly by non-technical managers.

---

## Non-Goals (Out of Scope for v1)
- Live bi-directional integration with Jira/Confluence REST APIs (v1 focuses on file export uploads).
- Complex enterprise multi-tenant authentication or OAuth / SSO.
- Modifying or writing back into original source files (read-only analytical processing).
- Multi-cloud cluster orchestration.

---

## Users & Personas
- **Operations & Project Managers**: Non-technical team leads who receive Confluence HTML pages or Word documents containing tracking tables and need rapid visibility into SLA compliance, overdue items, and severity without manual spreadsheet gymnastics.
- **Developers & Maintainers**: Engineers who need to maintain, extend, or add custom parsing rules and SLA metrics in a clean, human-readable modular codebase.

---

## Constraints
- **Environment**: Python 3.10+ on Windows / macOS / Linux.
- **Frontend Simplicity**: Pure frontend assets (Tailwind CSS via CDN, Chart.js) served directly by FastAPI without requiring separate Node.js / npm build steps, ensuring frictionless local installation and execution.
- **Legacy Compatibility**: Parsing logic and SLA computation rules must match or improve upon the business logic in the 1611-line legacy script once provided.

---

## Success Criteria
- [ ] Clean folder hierarchy established (`config/`, `core/`, `web/`) with 0 monolithic scripts.
- [ ] Ingestion verified for both HTML/Confluence and DOCX exports containing tabular records.
- [ ] Correct extraction and calculation of SLA metrics (elapsed duration, overdue days, breach threshold flags).
- [ ] Functional FastAPI web server serving a responsive multi-tab dashboard.
- [ ] Drag-and-drop file uploader handles files and renders processed results in under 3 seconds for standard export sizes.
- [ ] Visual charts display severity distributions and overdue analytics clearly.
- [ ] Code passes linting/type checks and includes human-readable docstrings on all public functions/classes.

---

## Technical Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| REQ-01 | Modular project structure (`config/`, `core/`, `web/`) | Must-have | Clear separation of concerns |
| REQ-02 | HTML & Confluence table parser | Must-have | BeautifulSoup4 based table extraction |
| REQ-03 | DOCX table parser | Must-have | python-docx based table extraction |
| REQ-04 | SLA breach detection & overdue calculation engine | Must-have | Duration, threshold comparison, overdue days |
| REQ-05 | Pydantic data models for records and summary metrics | Must-have | Strict typing and validation |
| REQ-06 | FastAPI backend with upload and query endpoints | Must-have | REST API for processing files and returning data |
| REQ-07 | Drag-and-drop web uploader with instant feedback | Must-have | Zero-code UX for non-technical managers |
| REQ-08 | Multi-tab UI (Upload, Breached Records, Visual Dashboards, Settings) | Must-have | Modern responsive layout (Tailwind CSS) |
| REQ-09 | Interactive visual dashboard charts | Must-have | Chart.js visual metrics (severity, overdue distribution) |
| REQ-10 | Configurable SLA thresholds & column mapping | Should-have | Config file (YAML/JSON) for thresholds |

---

*Last updated: 2026-10-13*
