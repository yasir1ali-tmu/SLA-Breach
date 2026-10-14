---
phase: 3
plan: 1
wave: 1
depends_on: []
files_modified:
  - web/__init__.py
  - web/app.py
  - web/api/__init__.py
  - web/api/routes.py
  - tests/test_api.py
autonomous: true
gap_closure: false

must_haves:
  truths:
    - "FastAPI application factory creates and configures the ASGI app with CORS and settings"
    - "GET /api/health returns 200 OK with system status, app name, and version"
    - "GET /api/rules returns 200 OK with active SLA priority thresholds, severity rules, and upload limits"
    - "POST /api/upload accepts .html, .htm, and .docx files, validating file size and format"
    - "POST /api/upload extracts tables via core.parsers and computes SLA metrics via SlaEngine"
    - "POST /api/upload rejects empty files (0 bytes) and unsupported file formats with 400 Bad Request"
    - "POST /api/upload rejects files exceeding maximum configured upload size with 413 Payload Too Large"
    - "All unit and API integration tests in tests/test_api.py pass cleanly"
  artifacts:
    - web/app.py
    - web/api/routes.py
    - tests/test_api.py
---

# Plan 3.1: FastAPI Server Scaffolding and REST API Endpoints

<objective>
Implement the FastAPI backend application factory (`web/app.py`) and REST API endpoints (`web/api/routes.py`) for file ingestion, validation, table extraction, and SLA calculation.

The API exposes:
- `GET /api/health`: System health status, version, and server timestamp.
- `GET /api/rules`: Active SLA configuration, priority targets, severity rules, and upload constraints.
- `POST /api/upload`: Multi-format file uploader accepting Confluence/HTML and Word DOCX exports, verifying file size and extension, parsing tabular ticket records via `core.parsers`, computing SLA metrics via `SlaEngine`, and returning comprehensive JSON with record details and summary KPIs.

Comprehensive integration tests in `tests/test_api.py` verify happy-path parsing, error handling (empty files, invalid extensions, oversized payloads), and response schema compliance.

Purpose: Provide a robust, typed backend API enabling automated SLA computation from uploaded export files for frontend consumers and headless integration.
Output: `web/app.py`, `web/api/routes.py`, and `tests/test_api.py`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- config/settings.py
- config/default_sla_rules.yaml
- core/models/sla.py
- core/parsers/html_parser.py
- core/parsers/docx_parser.py
- core/sla/engine.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement FastAPI application factory and lifecycle configuration</name>
  <files>
    web/__init__.py
    web/app.py
    web/api/__init__.py
  </files>
  <action>
    1. Create `web/app.py` with an application factory function `create_app() -> FastAPI`:
       - Load application configuration dynamically using `config.settings.get_settings()`.
       - Initialize `FastAPI` instance with:
         * `title=settings.app_name` ("SLA Breach Dashboard & Analyzer").
         * `version=settings.app_version` ("1.0.0").
         * `debug=settings.debug`.
         * `docs_url="/api/docs"`, `redoc_url="/api/redoc"`, `openapi_url="/api/openapi.json"`.
       - Add `CORSMiddleware` (allow origins `["*"]`, allow credentials `True`, allow methods `["*"]`, allow headers `["*"]`) to support local development and browser fetch requests.
       - Configure custom exception handlers:
         * `HTTPException`: return standard JSON `{ "detail": exc.detail, "status_code": exc.status_code }`.
         * Catch-all `Exception`: log error and return status 500 `{ "detail": "Internal server error", "error": str(exc) }`.
       - Conditionally mount static files if directory exists (`web/static`):
         * `if Path("web/static").is_dir(): app.mount("/static", StaticFiles(directory="web/static"), name="static")`.
       - Include API router from `web.api.routes` under prefix `"/api"`.
       - Expose module-level `app = create_app()` for ASGI runners (`uvicorn web.app:app`).
    2. Ensure `web/__init__.py` and `web/api/__init__.py` expose clean module imports.

    AVOID: hardcoding configuration values directly in `app.py`. USE `config.settings.get_settings()`.
    AVOID: crashing on app initialization if `web/static` or `web/templates` do not exist yet. Check directory existence before mounting.
  </action>
  <verify>
    python -c "from web.app import create_app; app = create_app(); assert app.title == 'SLA Breach Dashboard & Analyzer'; print('FastAPI app factory successfully verified')"
  </verify>
  <done>
    `web/app.py` instantiates FastAPI cleanly with settings, CORS middleware, API router prefix, and exception handlers.
  </done>
</task>

<task type="auto">
  <name>Task 2: Implement REST API endpoints for health, rules, and file upload</name>
  <files>
    web/api/routes.py
    web/api/__init__.py
  </files>
  <action>
    1. Create `web/api/routes.py` defining `router = APIRouter()`:
       - Endpoint `GET /health`:
         * Returns JSON: `{"status": "ok", "app": settings.app_name, "version": settings.app_version, "timestamp": datetime.now(timezone.utc).isoformat()}`.
       - Endpoint `GET /rules`:
         * Returns active configuration from `get_sla_rules()` and `get_settings()`:
           - `sla_thresholds`: default target days and priority targets dictionary.
           - `severity_rules`: warning threshold pct, breached threshold days, critical overdue days.
           - `column_mappings`: aliases for ticket_id, summary, status, priority, dates, team.
           - `allowed_extensions`: list of supported file formats.
           - `max_upload_size_mb`: maximum allowed upload size.
       - Endpoint `POST /upload`:
         * Accepts `file: UploadFile = File(...)`.
         * Extension validation:
           - Extract extension: `ext = Path(file.filename or '').suffix.lower()`.
           - If `ext not in settings.allowed_extensions`:
             Raise `HTTPException(status_code=400, detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(settings.allowed_extensions)}")`.
         * Asynchronously read content: `content = await file.read()`.
         * Size and emptiness validation:
           - If `len(content) == 0`:
             Raise `HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")`.
           - Max size check: `max_bytes = settings.max_upload_size_mb * 1024 * 1024`.
           - If `len(content) > max_bytes`:
             Raise `HTTPException(status_code=413, detail=f"File exceeds maximum upload limit of {settings.max_upload_size_mb} MB.")`.
         * Parsing dispatch:
           - If `ext in [".html", ".htm"]`:
             Decode bytes to string using utf-8 with fallback replacement: `html_text = content.decode("utf-8", errors="replace")`.
             Invoke `parse_html_table(html_text, source_filename=file.filename)`.
           - If `ext == ".docx"`:
             Invoke `parse_docx_table(content, source_filename=file.filename)`.
         * SLA calculation:
           - Initialize `engine = SlaEngine()`.
           - Process extraction: `engine.process_extraction_result(extraction_result)`.
           - Compute metrics: `summary_metrics = engine.calculate_summary_metrics(extraction_result.parsed_records)`.
         * Return response dictionary containing:
           - `source_filename`: `file.filename`
           - `file_type`: `extraction_result.file_type`
           - `extracted_at`: `extraction_result.extracted_at.isoformat()`
           - `total_rows`: `extraction_result.total_rows`
           - `parsed_count`: `len(extraction_result.parsed_records)`
           - `unparsed_rows`: `extraction_result.unparsed_rows`
           - `errors`: `extraction_result.errors`
           - `warnings`: `extraction_result.warnings`
           - `metrics`: `summary_metrics.model_dump()`
           - `records`: `[r.model_dump() for r in extraction_result.parsed_records]`
    2. Export `router` from `web/api/__init__.py`.

    AVOID: synchronous file read blocking event loop. USE `await file.read()`.
    AVOID: discarding unmapped columns. Ensure `raw_fields` in `SlaRecord` is preserved in the JSON response.
  </action>
  <verify>
    python -c "from web.api.routes import router; paths = [r.path for r in router.routes]; assert '/health' in paths and '/rules' in paths and '/upload' in paths; print('All API route endpoints verified:', paths)"
  </verify>
  <done>
    All three REST API endpoints (`/health`, `/rules`, `/upload`) are implemented with extension validation, size checking, table extraction, and SLA calculation.
  </done>
</task>

<task type="auto">
  <name>Task 3: Implement comprehensive API test suite</name>
  <files>
    tests/test_api.py
  </files>
  <action>
    1. Create `tests/test_api.py` using `fastapi.testclient.TestClient`:
       - `test_health_endpoint`:
         * `client.get("/api/health")` returns 200 OK.
         * JSON contains `status == "ok"` and `version == "1.0.0"`.
       - `test_rules_endpoint`:
         * `client.get("/api/rules")` returns 200 OK.
         * JSON contains `sla_thresholds`, `severity_rules`, and `allowed_extensions`.
       - `test_upload_html_success`:
         * Create mock HTML table with 2 ticket rows (including key, summary, priority, created date).
         * Send `POST /api/upload` as multipart/form-data.
         * Assert 200 OK.
         * Assert `total_rows == 2`, `parsed_count == 2`.
         * Assert `metrics["total_records"] == 2`.
         * Assert records have calculated `sla_target_days`, `elapsed_days`, `overdue_days`, and `severity`.
       - `test_upload_docx_success`:
         * Construct an in-memory `.docx` document with `docx.Document()`, add table with ticket headers and sample row.
         * Save to `io.BytesIO` and upload to `POST /api/upload`.
         * Assert 200 OK, `parsed_count >= 1`.
       - `test_upload_unsupported_extension`:
         * Upload file with `.pdf` or `.txt` extension.
         * Assert status 400 Bad Request with informative detail message.
       - `test_upload_empty_file`:
         * Upload empty file (0 bytes).
         * Assert status 400 Bad Request with "empty" detail.
       - `test_upload_size_limit_exceeded`:
         * Mock or test upload exceeding `max_upload_size_mb`.
         * Assert status 413 Payload Too Large.
       - `test_upload_html_without_ticket_tables`:
         * Upload HTML containing table without ticket ID column.
         * Assert 200 OK, `total_rows == 0`, and warnings list is non-empty.
    2. Run test suite to verify 100% passes.

    AVOID: writing temporary files to disk. USE `io.BytesIO` for in-memory file uploads.
  </action>
  <verify>
    pytest tests/test_api.py -v
  </verify>
  <done>
    `tests/test_api.py` passes completely with all endpoints tested for valid processing, invalid formats, empty files, and size limits.
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:
- [ ] `GET /api/health` returns 200 OK with system status
- [ ] `GET /api/rules` returns 200 OK with configured SLA thresholds
- [ ] `POST /api/upload` parses HTML and DOCX files into calculated SLA records
- [ ] `POST /api/upload` rejects invalid extensions and empty files with 400 Bad Request
- [ ] `POST /api/upload` rejects oversized files with 413 Payload Too Large
- [ ] All tests in `tests/test_api.py` pass cleanly
- [ ] Entire test suite `pytest tests/ -v` passes with no regressions
</verification>

<success_criteria>
- [ ] All 3 tasks verified passing
- [ ] Must-haves confirmed
- [ ] No regressions in existing test suites
</success_criteria>
