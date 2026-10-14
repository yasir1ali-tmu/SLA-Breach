---
phase: 1
plan: 1
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - pyproject.toml
  - config/__init__.py
  - core/__init__.py
  - core/models/__init__.py
  - core/models/sla.py
  - core/parsers/__init__.py
  - core/sla/__init__.py
  - core/analytics/__init__.py
  - web/__init__.py
  - web/api/__init__.py
  - tests/__init__.py
  - tests/test_models.py
autonomous: true
gap_closure: false

must_haves:
  truths:
    - "Clean modular directory architecture is established with importable packages"
    - "Project dependencies are documented in requirements.txt with pinned/compatible versions"
    - "Pydantic v2 data models for SlaRecord, SeverityLevel, ExtractionResult, and SlaSummaryMetrics validate data and serialize to JSON correctly"
    - "Unit tests for core models pass cleanly"
  artifacts:
    - requirements.txt
    - pyproject.toml
    - core/models/sla.py
    - tests/test_models.py
---

# Plan 1.1: Project Scaffolding, Dependencies, and Core Data Models

<objective>
Establish the foundational modular architecture for the SLA Breach processing platform.
This includes setting up package scaffolding (`config/`, `core/`, `web/`, `tests/`), defining required Python runtime dependencies in `requirements.txt`, configuring pytest in `pyproject.toml`, and implementing strict Pydantic v2 schemas (`SlaRecord`, `SeverityLevel`, `ExtractionResult`, `SlaSummaryMetrics`) with unit tests.

Purpose: Provide a strongly-typed, cleanly organized foundation so parsers, calculation engines, and web APIs can import shared schemas without circular dependencies or type ambiguity.
Output: Scaffolding packages, `requirements.txt`, `pyproject.toml`, `core/models/sla.py`, and `tests/test_models.py`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- .gsd/REQUIREMENTS.md
- .gsd/ROADMAP.md
- .gsd/DECISIONS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Establish modular package scaffolding and project dependencies</name>
  <files>
    requirements.txt
    pyproject.toml
    config/__init__.py
    core/__init__.py
    core/models/__init__.py
    core/parsers/__init__.py
    core/sla/__init__.py
    core/analytics/__init__.py
    web/__init__.py
    web/api/__init__.py
    tests/__init__.py
  </files>
  <action>
    1. Create the modular package directory layout with explicit `__init__.py` files:
       - `config/__init__.py`
       - `core/__init__.py`
       - `core/models/__init__.py`
       - `core/parsers/__init__.py`
       - `core/sla/__init__.py`
       - `core/analytics/__init__.py`
       - `web/__init__.py`
       - `web/api/__init__.py`
       - `tests/__init__.py`
    2. Create `requirements.txt` with required production and development dependencies:
       - fastapi>=0.110.0
       - uvicorn[standard]>=0.28.0
       - pydantic>=2.6.0
       - pydantic-settings>=2.2.0
       - pyyaml>=6.0.1
       - python-docx>=1.1.0
       - beautifulsoup4>=4.12.0
       - lxml>=5.1.0
       - pandas>=2.2.0
       - python-multipart>=0.0.9 (required by FastAPI for file upload endpoints)
       - jinja2>=3.1.3 (required by FastAPI for template rendering)
       - pytest>=8.0.0
    3. Create `pyproject.toml` with pytest configuration:
       - Set `pythonpath = ["."]` so imports work cleanly from project root.
       - Set `testpaths = ["tests"]`.
       - Add standard Python build / packaging metadata.

    AVOID: Omitting `python-multipart` or `jinja2`, which causes runtime crashes during later FastAPI file handling and template serving.
    USE: Compatible modern package version bounds supporting Python 3.10+.
  </action>
  <verify>
    python -c "import config, core, web; print('Scaffolding packages importable successfully')"
  </verify>
  <done>
    All specified directories and `__init__.py` files exist, `requirements.txt` and `pyproject.toml` are created, and `python -c "import config, core, web"` executes with returncode 0.
  </done>
</task>

<task type="auto">
  <name>Task 2: Implement core Pydantic data schemas and unit tests</name>
  <files>
    core/models/sla.py
    core/models/__init__.py
    tests/test_models.py
  </files>
  <action>
    1. Create `core/models/sla.py` using Pydantic v2 containing:
       - `SeverityLevel(str, Enum)`:
         - Values: `OK = "OK"`, `WARNING = "WARNING"`, `CRITICAL = "CRITICAL"`, `BREACHED = "BREACHED"`.
         - Helper method or property to return badge color classes or display names.
       - `SlaRecord(BaseModel)`:
         - `id`: str (generated default UUID string or issue key)
         - `key`: str (e.g. ticket reference "PROJ-1234")
         - `summary`: Optional[str] = None
         - `team`: Optional[str] = None (assignee, owner, or component)
         - `status`: Optional[str] = None
         - `priority`: Optional[str] = None (e.g. "P1", "P2", "Critical", "Major")
         - `created_date`: Optional[datetime] = None
         - `resolved_date`: Optional[datetime] = None
         - `due_date`: Optional[datetime] = None
         - `sla_target_days`: Optional[float] = None
         - `elapsed_days`: Optional[float] = None
         - `overdue_days`: Optional[float] = None
         - `is_breached`: bool = False
         - `severity`: SeverityLevel = SeverityLevel.OK
         - `raw_fields`: Dict[str, Any] = Field(default_factory=dict) (stores any unmapped or original column values for lossless fidelity)
         - `model_config = ConfigDict(populate_by_name=True, extra="ignore")`
       - `ExtractionResult(BaseModel)`:
         - `source_filename`: str
         - `file_type`: str (e.g., "html", "docx")
         - `extracted_at`: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
         - `total_rows`: int = 0
         - `parsed_records`: List[SlaRecord] = Field(default_factory=list)
         - `unparsed_rows`: int = 0
         - `errors`: List[str] = Field(default_factory=list)
         - `warnings`: List[str] = Field(default_factory=list)
       - `SlaSummaryMetrics(BaseModel)`:
         - `total_records`: int = 0
         - `breached_count`: int = 0
         - `warning_count`: int = 0
         - `compliant_count`: int = 0
         - `breach_rate_pct`: float = 0.0
         - `avg_overdue_days`: float = 0.0
         - `max_overdue_days`: float = 0.0
         - `by_severity`: Dict[str, int] = Field(default_factory=dict)
         - `by_team`: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    2. In `core/models/__init__.py`, export `SeverityLevel`, `SlaRecord`, `ExtractionResult`, and `SlaSummaryMetrics`.
    3. In `tests/test_models.py`, write comprehensive unit tests covering:
       - Instantiation of `SlaRecord` with minimal and full parameters.
       - Serialization to dict and JSON (`model_dump()`, `model_dump_json()`).
       - Handling of `raw_fields` preservation for unmapped metadata.
       - Instantiation and validation of `ExtractionResult` and `SlaSummaryMetrics`.
       - Validation error checks when required fields (`key`) are missing or invalid types are supplied.

    AVOID: Using deprecated Pydantic v1 idioms (e.g. `class Config:`, `.dict()`). Use Pydantic v2 `model_config = ConfigDict(...)` and `.model_dump()`.
    USE: Strict type hints, docstrings on every model class, and timezone-aware datetimes where appropriate.
  </action>
  <verify>
    pytest tests/test_models.py -v
  </verify>
  <done>
    `core/models/sla.py` exports `SeverityLevel`, `SlaRecord`, `ExtractionResult`, and `SlaSummaryMetrics`. All tests in `tests/test_models.py` pass with zero failures.
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:
- [ ] Packages `config`, `core`, `core.models`, `core.parsers`, `core.sla`, `core.analytics`, `web`, `web.api` are importable.
- [ ] `requirements.txt` contains FastAPI, uvicorn, pydantic, pyyaml, python-docx, beautifulsoup4, pandas, and pytest.
- [ ] `pyproject.toml` defines pytest testpaths and pythonpath.
- [ ] Pydantic models validate data structures, serialize cleanly, and have passing unit tests.
</verification>

<success_criteria>
- [ ] All tasks verified passing with runnable commands.
- [ ] Must-haves confirmed against REQ-01 and REQ-02.
- [ ] Unit tests pass via `pytest tests/test_models.py`.
</success_criteria>
