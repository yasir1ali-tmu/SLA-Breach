---
phase: 2
plan: 2
wave: 2
depends_on:
  - 1-PLAN
files_modified:
  - core/parsers/date_parser.py
  - core/parsers/__init__.py
  - core/sla/severity.py
  - core/sla/engine.py
  - core/sla/__init__.py
  - tests/test_sla_engine.py
autonomous: true
gap_closure: false

must_haves:
  truths:
    - "Multi-format date parser handles all templates in default_sla_rules.yaml into timezone-aware datetimes"
    - "Date parser handles dirty strings, whitespace, and invalid formats safely without raising uncaught exceptions"
    - "Breach severity logic categorizes records into OK, WARNING, BREACHED, and CRITICAL according to configured rules"
    - "SLA calculation engine computes target days from ticket priority or default fallback"
    - "Elapsed duration (days/hours) and overdue days are accurately computed for both resolved and open tickets"
    - "Summary metrics calculation aggregates breach rates, averages, max overdue days, and team distributions"
    - "Comprehensive unit tests in tests/test_sla_engine.py pass cleanly"
  artifacts:
    - core/parsers/date_parser.py
    - core/sla/severity.py
    - core/sla/engine.py
    - tests/test_sla_engine.py
---

# Plan 2.2: SLA Calculation Engine, Multi-Format Date Parser, and Severity Evaluator

<objective>
Implement the core SLA calculation engine (`core/sla/engine.py`), resilient multi-format date parser (`core/parsers/date_parser.py`), and breach severity evaluator (`core/sla/severity.py`) driven by configuration rules (`config/default_sla_rules.yaml`).
The engine computes SLA target days, elapsed durations (days/hours), overdue metrics, breach flags, and severity classifications across individual and batch `SlaRecord` collections, and generates aggregated `SlaSummaryMetrics` with complete test coverage in `tests/test_sla_engine.py`.

Purpose: Provide precise, mathematically verified SLA calculations and metric aggregations so operations managers can instantly identify compliance status, high-risk items, and team-level bottlenecks.
Output: `core/parsers/date_parser.py`, `core/sla/severity.py`, `core/sla/engine.py`, updated `core/sla/__init__.py` and `core/parsers/__init__.py`, and `tests/test_sla_engine.py`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- config/settings.py
- config/default_sla_rules.yaml
- core/models/sla.py
- .gsd/phases/2/1-PLAN.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement resilient multi-format date parser</name>
  <files>
    core/parsers/date_parser.py
    core/parsers/__init__.py
  </files>
  <action>
    1. Create `core/parsers/date_parser.py`:
       - Define `parse_datetime(value: Union[str, datetime, Any], formats: Optional[List[str]] = None, default_tz: str = "UTC") -> Optional[datetime]`:
         - Returns `value` directly if already a `datetime`, ensuring timezone awareness (attach UTC if naive).
         - Returns `None` if `value` is `None`, empty string, or non-string/non-datetime.
         - Cleans string: strips whitespace, strips enclosing quotes, replaces multiple spaces and non-breaking spaces (`\xa0`).
         - Formats list: uses provided `formats` or retrieves `get_sla_rules().date_parsing.formats`.
           Must match configured patterns:
           - `%Y-%m-%d %H:%M:%S`, `%Y-%m-%d %H:%M`, `%Y-%m-%d`
           - `%d/%b/%y %I:%M %p`, `%d-%b-%Y`, `%b %d, %Y %I:%M %p`
           - `%d/%m/%Y %H:%M:%S`, `%d/%m/%Y %H:%M`, `%d/%m/%Y`
           - `%m/%d/%Y %I:%M:%S %p`, `%m/%d/%Y %I:%M %p`, `%m/%d/%Y`
         - Iterates through format patterns calling `datetime.strptime(cleaned, fmt)`.
         - Fallback parsing:
           - Tries `datetime.fromisoformat(cleaned)`.
           - Normalizes common textual variations (e.g., month abbreviations, am/pm casing).
         - Normalizes all parsed datetimes to timezone-aware UTC (`timezone.utc`).
         - Returns `None` on unparseable inputs without raising uncaught exceptions (unless explicit `strict: bool = True` is requested).
       - Define convenience helper `parse_date_safe(value: Any) -> Optional[datetime]` that wraps `parse_datetime`.
    2. Update `core/parsers/__init__.py` to export `parse_datetime` and `parse_date_safe`.

    AVOID: Returning naive datetimes that cause `TypeError` during later date comparisons.
    USE: Formats loaded from `get_sla_rules()`, defensive exception handling, and UTC normalization.
  </action>
  <verify>
    python -c "from core.parsers.date_parser import parse_datetime; assert parse_datetime('2024-05-10 14:30:00') is not None; assert parse_datetime('10/May/24 02:30 PM') is not None; assert parse_datetime('10/05/2024') is not None; assert parse_datetime('invalid-date') is None; print('Date parser verification passed')"
  </verify>
  <done>
    `core/parsers/date_parser.py` safely parses varied date formats into timezone-aware UTC `datetime` objects, returning `None` for invalid or empty values.
  </done>
</task>

<task type="auto">
  <name>Task 2: Implement severity evaluator and SLA calculation engine</name>
  <files>
    core/sla/severity.py
    core/sla/engine.py
    core/sla/__init__.py
  </files>
  <action>
    1. Create `core/sla/severity.py`:
       - Define `evaluate_severity(elapsed_days: float, target_days: float, overdue_days: float, rules: Optional[SeverityRulesConfig] = None) -> SeverityLevel`:
         - Retrieves `rules = rules or get_sla_rules().severity_rules`.
         - Evaluation precedence:
           1. If `overdue_days > rules.critical_overdue_days` (default > 3.0 days): return `SeverityLevel.CRITICAL`.
           2. Else if `overdue_days > rules.breached_threshold_days` (default > 0.0 days): return `SeverityLevel.BREACHED`.
           3. Else if `target_days > 0` and `(elapsed_days / target_days) * 100.0 >= rules.warning_threshold_pct` (default >= 80.0%): return `SeverityLevel.WARNING`.
           4. Else: return `SeverityLevel.OK`.
    2. Create `core/sla/engine.py`:
       - Define `class SlaEngine`:
         - `__init__(self, rules: Optional[SlaRulesConfig] = None)`: initializes engine with rules or `get_sla_rules()`.
         - `resolve_target_days(self, priority: Optional[str]) -> float`:
           - Matches priority against `rules.sla_thresholds.priority_targets_days` (case-insensitive lookup: "P1", "Blocker" -> 1.0; "P2", "Critical" -> 2.0; "P3", "Major" -> 5.0; etc.).
           - Falls back to `rules.sla_thresholds.default_target_days` (5.0 days) when priority is missing or unrecognized.
         - `calculate_record(self, record: SlaRecord, as_of: Optional[datetime] = None) -> SlaRecord`:
           - Target days: if `record.sla_target_days` is None or 0, sets `record.sla_target_days = self.resolve_target_days(record.priority)`.
           - Target duration: `target_days = record.sla_target_days`.
           - Reference end time: uses `record.resolved_date` if present; otherwise uses `as_of or datetime.now(timezone.utc)`.
           - When `record.created_date` exists:
             - Normalizes created date and end time to timezone-aware UTC.
             - Computes elapsed duration: `delta = end_time - record.created_date`.
             - `elapsed_days = round(max(0.0, delta.total_seconds() / 86400.0), 2)`.
             - Sets `record.elapsed_days = elapsed_days`.
             - Computes overdue days:
               - If `record.due_date` is provided: `due_delta = end_time - record.due_date`; `overdue_days = round(max(0.0, due_delta.total_seconds() / 86400.0), 2)`.
               - Else: `overdue_days = round(max(0.0, elapsed_days - target_days), 2)`.
             - Sets `record.overdue_days = overdue_days`.
             - Sets `record.is_breached = overdue_days > self.rules.severity_rules.breached_threshold_days`.
             - Sets `record.severity = evaluate_severity(elapsed_days, target_days, overdue_days, self.rules.severity_rules)`.
           - Returns updated `record`.
         - `calculate_batch(self, records: List[SlaRecord], as_of: Optional[datetime] = None) -> List[SlaRecord]`:
           - Applies `calculate_record` to all records in the list.
         - `calculate_summary_metrics(self, records: List[SlaRecord]) -> SlaSummaryMetrics`:
           - Aggregates:
             - `total_records = len(records)`
             - `breached_count = sum(1 for r in records if r.is_breached)`
             - `warning_count = sum(1 for r in records if r.severity == SeverityLevel.WARNING)`
             - `compliant_count = sum(1 for r in records if r.severity == SeverityLevel.OK)`
             - `breach_rate_pct = round((breached_count / total_records) * 100.0, 1)` if total_records > 0 else 0.0
             - `avg_overdue_days`: average `overdue_days` for breached records, rounded to 2 decimal places (or 0.0 if no breaches)
             - `max_overdue_days`: maximum `overdue_days` across all records (or 0.0)
             - `by_severity`: counts mapped by severity enum value (`{"OK": X, "WARNING": Y, "CRITICAL": Z, "BREACHED": W}`)
             - `by_team`: dictionary of team names mapping to `{"breached": X, "total": Y}`
           - Returns instantiated `SlaSummaryMetrics`.
         - `process_extraction_result(self, result: ExtractionResult, as_of: Optional[datetime] = None) -> ExtractionResult`:
           - Passes `result.parsed_records` through `calculate_batch` and updates the extraction result.
    3. Update `core/sla/__init__.py` to export `SlaEngine` and `evaluate_severity`.

    AVOID: ZeroDivisionError, comparing naive and aware datetimes, or negative overdue day values.
    USE: Explicit UTC timezone normalization, `round(..., 2)`, and standard priority mapping rules.
  </action>
  <verify>
    python -c "from datetime import datetime, timezone, timedelta; from core.models.sla import SlaRecord, SeverityLevel; from core.sla.engine import SlaEngine; engine = SlaEngine(); now = datetime.now(timezone.utc); rec = SlaRecord(key='TEST-100', priority='P1', created_date=now - timedelta(days=5)); processed = engine.calculate_record(rec, as_of=now); assert processed.is_breached is True and processed.severity == SeverityLevel.CRITICAL and processed.overdue_days >= 4.0; print('SLA engine verification passed')"
  </verify>
  <done>
    `core/sla/severity.py` and `core/sla/engine.py` are implemented, providing priority-based target resolution, elapsed/overdue calculation, severity rating, batch calculation, and KPI summary generation.
  </done>
</task>

<task type="auto">
  <name>Task 3: Implement comprehensive unit tests for SLA calculation engine and date parser</name>
  <files>
    tests/test_sla_engine.py
  </files>
  <action>
    Create `tests/test_sla_engine.py` with comprehensive unit tests:
    1. Date Parser Tests:
       - Standard ISO formats (`"2024-01-15 10:30:00"`, `"2024-01-15"`).
       - Slash formats with month names and 12-hour AM/PM (`"15/Jan/24 10:30 AM"`).
       - US/EU slash formats (`"15/01/2024"`, `"01/15/2024"`).
       - Whitespace resilience, empty string handling, invalid date handling (returns None).
       - Naive vs aware inputs (both return UTC aware datetimes).
    2. Severity Categorization Tests:
       - Compliant record (< 80% target elapsed) -> `SeverityLevel.OK`.
       - Warning record (>= 80% and <= 100% target elapsed, 0 overdue) -> `SeverityLevel.WARNING`.
       - Breached record (> 0.0 days overdue, <= 3.0 days overdue) -> `SeverityLevel.BREACHED`.
       - Critical record (> 3.0 days overdue) -> `SeverityLevel.CRITICAL`.
    3. SLA Engine Calculation Tests:
       - Priority target lookup: "P1" -> 1.0, "P2" -> 2.0, "P3" -> 5.0, "Blocker" -> 1.0, "Major" -> 5.0, unrecognized priority -> 5.0 default.
       - Resolved ticket: elapsed time computed between `created_date` and `resolved_date`.
       - Open ticket: elapsed time computed between `created_date` and fixed `as_of` date.
       - Explicit `due_date`: overdue days measured relative to `due_date`.
       - Fallback `due_date`: overdue days measured relative to `created_date + target_days`.
       - Batch calculation preserves all record fields and metadata.
       - Summary metrics aggregation:
         - Verifies `total_records`, `breached_count`, `warning_count`, `compliant_count`.
         - Verifies `breach_rate_pct`, `avg_overdue_days`, `max_overdue_days`.
         - Verifies `by_severity` and `by_team` breakdown dicts.
         - Handles empty records list without division by zero.

    AVOID: Clock-dependent assertions that fail if test runs at midnight; pass deterministic `as_of` datetimes into test calls.
    USE: Pytest parameterization, `pytest.approx` for floating point comparisons, and fixed UTC test dates.
  </action>
  <verify>
    pytest tests/test_sla_engine.py -v
  </verify>
  <done>
    `tests/test_sla_engine.py` contains unit tests covering all date parsing formats, severity evaluation levels, SLA engine calculations, and metric aggregations, with 100% passing tests.
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:
- [ ] `core/parsers/date_parser.py`, `core/sla/severity.py`, and `core/sla/engine.py` are importable.
- [ ] Date parser correctly handles all formats in `config/default_sla_rules.yaml`.
- [ ] Severity evaluator assigns OK, WARNING, BREACHED, and CRITICAL accurately.
- [ ] SLA engine calculates durations, overdue days, breach flags, and summary metrics.
- [ ] All unit tests in `tests/test_sla_engine.py` pass cleanly.
</verification>

<success_criteria>
- [ ] All 3 tasks verified passing with runnable commands.
- [ ] Must-haves confirmed against REQ-04 and REQ-05.
- [ ] Unit tests pass via `pytest tests/test_sla_engine.py`.
</success_criteria>
