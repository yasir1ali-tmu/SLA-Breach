# DECISIONS.md — Architecture Decision Records

> **Purpose**: Log significant technical decisions and their rationale.

---

## Decisions

## [DECISION-001] FastAPI with Vanilla Tailwind & JS UI

**Date**: 2026-10-13
**Status**: Accepted

### Context
Managers require an intuitive, multi-tab web application with a drag-and-drop file uploader that is simple to run locally without managing separate node / frontend build toolchains.

### Decision
Use **FastAPI** as the backend web server with HTML templates and Tailwind CSS (via CDN) + vanilla JavaScript / Chart.js for the multi-tab user interface.

### Rationale
- Pure Python environment without needing `npm`, `node`, or webpack.
- FastAPI provides high performance, automatic OpenAPI documentation, clean async I/O, and type validation via Pydantic.
- Single command execution (`uvicorn web.app:app --reload` or `python run.py`).

### Consequences
- Frontend components are authored in clean semantic HTML/JS rather than React/Vue, keeping dependencies zero-friction for local deployment.

### Alternatives Considered
- Streamlit: Evaluated, but FastAPI + custom modern UI offers total control over UI tabs, drag-and-drop visual flair, styling, and REST API access.
- Flask: FastAPI preferred for built-in Pydantic validation and async support.

---

## [DECISION-002] Visual Dashboard and Analytics Integration

**Date**: 2026-10-13
**Status**: Accepted

### Context
Managers need immediate visual clarity on SLA breach severity, overdue time distributions, and team/category volume.

### Decision
Integrate lightweight Chart.js into the frontend dashboard tab, fed by structured KPI aggregation endpoints from FastAPI.

### Rationale
- Renders responsive client-side charts without server overhead.
- Clean interactive tooltips and category filtering.

---

*Last updated: 2026-10-13*
