---
phase: 1
plan: 2
wave: 2
depends_on:
  - 1-PLAN
files_modified:
  - config/default_sla_rules.yaml
  - config/settings.py
  - tests/test_config.py
autonomous: true
gap_closure: false

must_haves:
  truths:
    - "Default SLA thresholds, severity criteria, and date formats are specified in default_sla_rules.yaml"
    - "Column alias mapping lists accommodate variations in Confluence and Word table headers"
    - "Settings and SLA rules are validated with Pydantic and accessible via cached getter functions"
    - "Column alias resolver accurately maps dirty/varied headers to canonical schema fields"
    - "Unit tests for config loading, header resolution, and settings overrides pass cleanly"
  artifacts:
    - config/default_sla_rules.yaml
    - config/settings.py
    - tests/test_config.py
---

# Plan 1.2: Configuration Management, SLA Rules & Column Mapping

<objective>
Implement the configuration management layer for the SLA Breach processing platform.
This includes creating `config/default_sla_rules.yaml` with default SLA targets per priority, breach severity thresholds, column alias mappings, and date formats; and building `config/settings.py` using `pydantic-settings` with type-safe schema models, cached loaders, and header resolution logic backed by unit tests in `tests/test_config.py`.

Purpose: Ensure SLA thresholds, warning percentages, and table column names are fully configurable without touching application code, enabling resilient ingestion across varied export formats.
Output: `config/default_sla_rules.yaml`, `config/settings.py`, and `tests/test_config.py`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- .gsd/REQUIREMENTS.md
- .gsd/ROADMAP.md
- .gsd/phases/1/1-PLAN.md
- core/models/sla.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Define default SLA rules and column mapping YAML configuration</name>
  <files>
    config/default_sla_rules.yaml
  </files>
  <action>
    Create `config/default_sla_rules.yaml` with the following comprehensive configuration sections:
    1. `application`:
       - `name`: "SLA Breach Dashboard & Analyzer"
       - `version`: "1.0.0"
       - `debug`: false
       - `max_upload_size_mb`: 25
       - `allowed_extensions`: [".html", ".htm", ".docx"]
    2. `sla_thresholds`:
       - `default_target_days`: 5.0
       - `priority_targets_days`:
         - `P1`: 1.0
         - `Blocker`: 1.0
         - `P2`: 2.0
         - `Critical`: 2.0
         - `P3`: 5.0
         - `Major`: 5.0
         - `P4`: 10.0
         - `Minor`: 10.0
         - `P5`: 15.0
         - `Trivial`: 15.0
    3. `severity_rules`:
       - `warning_threshold_pct`: 80.0 (elapsed time >= 80% of SLA target triggers WARNING)
       - `breached_threshold_days`: 0.0 (overdue days > 0 triggers BREACHED)
       - `critical_overdue_days`: 3.0 (overdue days > 3.0 triggers CRITICAL)
    4. `column_mappings`:
       - `ticket_id`: ["Key", "Issue key", "Issue Key", "Ticket", "Ticket ID", "ID", "Incident ID", "Reference", "Task Key", "Item #"]
       - `summary`: ["Summary", "Title", "Issue summary", "Description", "Topic", "Subject", "Item Description"]
       - `status`: ["Status", "State", "Issue Status", "Current Status", "Progress", "Ticket Status"]
       - `priority`: ["Priority", "Severity", "Urgency", "Level", "Importance"]
       - `created_date`: ["Created", "Created Date", "Creation Date", "Reported", "Date Created", "Open Date", "Reported Date", "Start Date"]
       - `resolved_date`: ["Resolved", "Resolution Date", "Closed", "Closed Date", "Date Resolved", "Completion Date", "End Date"]
       - `due_date`: ["Due Date", "Due", "Target Date", "SLA Due Date", "Deadline", "Target Resolution Date"]
       - `team`: ["Assignee", "Team", "Assigned Team", "Owner", "Component", "Group", "Assigned Group", "Department"]
    5. `date_parsing`:
       - `default_timezone`: "UTC"
       - `formats`:
         - "%Y-%m-%d %H:%M:%S"
         - "%Y-%m-%d %H:%M"
         - "%Y-%m-%d"
         - "%d/%b/%y %I:%M %p"
         - "%d/%m/%Y %H:%M:%S"
         - "%d/%m/%Y %H:%M"
         - "%d/%m/%Y"
         - "%m/%d/%Y %I:%M:%S %p"
         - "%m/%d/%Y %I:%M %p"
         - "%m/%d/%Y"
         - "%b %d, %Y %I:%M %p"
         - "%d-%b-%Y"

    AVOID: Omitting common column synonyms or casing variants, which leads to unmapped columns during table ingestion.
    USE: Clean structured YAML with documented units (e.g. days, percentages).
  </action>
  <verify>
    python -c "import yaml; data = yaml.safe_load(open('config/default_sla_rules.yaml', 'r', encoding='utf-8')); assert 'column_mappings' in data and 'sla_thresholds' in data; print('YAML valid and structurally complete')"
  </verify>
  <done>
    `config/default_sla_rules.yaml` exists, is syntactically valid YAML, and contains application settings, SLA thresholds, severity rules, column aliases, and date formats.
  </done>
</task>

<task type="auto">
  <name>Task 2: Build configuration loader, AppSettings, and column resolver in config/settings.py</name>
  <files>
    config/settings.py
    tests/test_config.py
  </files>
  <action>
    1. Create `config/settings.py`:
       - Define Pydantic models for configuration structure:
         - `SlaThresholdsConfig(BaseModel)`: `default_target_days: float = 5.0`, `priority_targets_days: Dict[str, float]`
         - `SeverityRulesConfig(BaseModel)`: `warning_threshold_pct: float = 80.0`, `breached_threshold_days: float = 0.0`, `critical_overdue_days: float = 3.0`
         - `ColumnMappingsConfig(BaseModel)`: alias lists for `ticket_id`, `summary`, `status`, `priority`, `created_date`, `resolved_date`, `due_date`, `team`.
         - `DateParsingConfig(BaseModel)`: `default_timezone: str = "UTC"`, `formats: List[str]`
         - `SlaRulesConfig(BaseModel)`: aggregates `sla_thresholds`, `severity_rules`, `column_mappings`, and `date_parsing`.
       - Define `AppSettings(BaseSettings)` inheriting from `pydantic_settings.BaseSettings`:
         - `app_name: str = "SLA Breach Dashboard & Analyzer"`
         - `app_version: str = "1.0.0"`
         - `debug: bool = False`
         - `host: str = "127.0.0.1"`
         - `port: int = 8000`
         - `max_upload_size_mb: int = 25`
         - `allowed_extensions: List[str] = [".html", ".htm", ".docx"]`
         - `rules_config_path: Path = Path("config/default_sla_rules.yaml")`
         - `model_config = SettingsConfigDict(env_prefix="SLA_", env_file=".env", extra="ignore")`
       - Implement loaders and utilities:
         - `load_sla_rules(config_path: Optional[Path | str] = None) -> SlaRulesConfig`:
           Reads YAML file, instantiates and validates `SlaRulesConfig`. Raises `FileNotFoundError` or `ValueError` with descriptive message if file is missing or invalid.
         - `@lru_cache(maxsize=1) def get_sla_rules() -> SlaRulesConfig`: Cached retrieval of default rules.
         - `@lru_cache(maxsize=1) def get_settings() -> AppSettings`: Cached retrieval of application settings.
         - `resolve_column_name(header: str, mappings: ColumnMappingsConfig) -> Optional[str]`:
           Normalizes input header (lowercase, strip whitespace, remove punctuation like colons/underscores) and searches for matches across mapping alias lists. Returns canonical field name (e.g., "ticket_id") or `None`.
         - `clear_config_caches() -> None`: Helper to clear LRU caches during testing or reloads.
    2. Create `tests/test_config.py` with comprehensive test suite:
       - Test loading default `SlaRulesConfig` from `config/default_sla_rules.yaml`.
       - Test `resolve_column_name` for diverse variants:
         - "Issue Key", "issue_key", "Key", "Ticket ID" -> "ticket_id"
         - "Created Date", "Date Created", "Open Date" -> "created_date"
         - "Assignee", "Assigned Team" -> "team"
         - "NonExistentHeader123" -> None
       - Test `AppSettings` defaults and environment variable overrides (`SLA_DEBUG=true`, `SLA_PORT=9000`).
       - Test error handling when loading from a non-existent file or corrupted YAML.

    AVOID: Unhandled exceptions or brittle exact-match comparisons for table column headers.
    USE: Robust normalization in `resolve_column_name`, type validation via Pydantic v2, and clean `@lru_cache` decorators.
  </action>
  <verify>
    pytest tests/test_config.py -v
  </verify>
  <done>
    `config/settings.py` provides `AppSettings`, `SlaRulesConfig`, `load_sla_rules`, and `resolve_column_name`. All unit tests in `tests/test_config.py` pass with zero errors.
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:
- [ ] `config/default_sla_rules.yaml` contains priority targets, severity rules, column aliases, and date formats.
- [ ] `config/settings.py` loads and validates configuration via Pydantic.
- [ ] Column alias resolution successfully maps common header synonyms to canonical fields.
- [ ] All unit tests in `tests/test_config.py` pass.
</verification>

<success_criteria>
- [ ] All tasks verified passing with runnable commands.
- [ ] Must-haves confirmed against REQ-10.
- [ ] Unit tests pass via `pytest tests/test_config.py`.
</success_criteria>
