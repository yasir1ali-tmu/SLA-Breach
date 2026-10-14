---
phase: 2
plan: 1
wave: 1
depends_on: []
files_modified:
  - core/parsers/html_parser.py
  - core/parsers/docx_parser.py
  - core/parsers/__init__.py
  - tests/test_parsers.py
autonomous: true
gap_closure: false

must_haves:
  truths:
    - "Confluence and HTML table parser extracts tabular rows into SlaRecord models"
    - "Word DOCX parser extracts tabular rows into SlaRecord models"
    - "Both parsers map column aliases dynamically using config.resolve_column_name"
    - "Unmapped columns and original values are preserved in SlaRecord.raw_fields"
    - "Parsers handle dirty data, missing headers, nested tables, and merged cells gracefully without crashes"
    - "ExtractionResult records total rows, parsed records, unparsed count, errors, and warnings"
    - "Comprehensive unit tests in tests/test_parsers.py pass cleanly"
  artifacts:
    - core/parsers/html_parser.py
    - core/parsers/docx_parser.py
    - core/parsers/__init__.py
    - tests/test_parsers.py
---

# Plan 2.1: Confluence/HTML and Word DOCX Table Extraction Modules

<objective>
Implement robust, modular table extraction parsers for Confluence/HTML exports (`core/parsers/html_parser.py`) and Word documents (`core/parsers/docx_parser.py`).
Both parsers inspect tabular structures, normalize dirty cell text, resolve column header synonyms to canonical fields using `config.settings.resolve_column_name`, construct typed `SlaRecord` models, preserve all unmapped columns in `raw_fields`, resiliently handle edge cases (nested tables, merged cells, missing headers, empty rows), and wrap outputs in an `ExtractionResult` model with comprehensive test coverage in `tests/test_parsers.py`.

Purpose: Enable non-technical managers to ingest real-world Confluence HTML exports and Word DOCX reports of varying structure without manual spreadsheet cleanup or code changes.
Output: `core/parsers/html_parser.py`, `core/parsers/docx_parser.py`, updated `core/parsers/__init__.py`, and `tests/test_parsers.py`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- config/settings.py
- config/default_sla_rules.yaml
- core/models/sla.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement Confluence and HTML table parser</name>
  <files>
    core/parsers/html_parser.py
    core/parsers/__init__.py
  </files>
  <action>
    1. Create `core/parsers/html_parser.py`:
       - Define `parse_html_table(html_content: Union[str, bytes], source_filename: str = "upload.html", rules: Optional[SlaRulesConfig] = None) -> ExtractionResult`:
         - Parses HTML using BeautifulSoup with `lxml` parser (fallback to `html.parser` if `lxml` is unavailable).
         - Retrieves configuration: `rules = rules or get_sla_rules()`.
         - Discovers all `<table>` elements in document (including standard tables and Confluence-specific `<table class="confluenceTable">`).
         - Resiliently handles nested tables: when inspecting cells in an outer table, strips or extracts inner table text cleanly without duplicating rows or misaligning columns.
         - Extracts and normalizes column headers:
           - Inspects `<th>` cells or first `<tr>` row.
           - Cleans whitespace (`\s+`, `\xa0`, HTML entities).
           - Resolves each header to a canonical field using `resolve_column_name(header, rules.column_mappings)`.
           - Identifies table containing ticket identifier (`ticket_id` or other canonical fields). If table has no matched columns, records a warning and inspects other tables.
         - Iterates through data rows:
           - Extracts cell texts matching mapped columns.
           - Maps `ticket_id` -> `SlaRecord.key`. If key is missing or blank, increments `unparsed_rows` and logs warning.
           - Maps `summary` -> `SlaRecord.summary`.
           - Maps `team` -> `SlaRecord.team`.
           - Maps `status` -> `SlaRecord.status`.
           - Maps `priority` -> `SlaRecord.priority`.
           - Maps date fields (`created_date`, `resolved_date`, `due_date`) attempting standard/ISO parsing or deferring raw strings to `raw_fields`.
           - Preserves all unmapped column headers and values in `SlaRecord.raw_fields[original_header] = cell_text` for lossless data retention.
           - Skips completely empty rows gracefully.
         - Wraps output in `ExtractionResult`:
           - `source_filename = source_filename`
           - `file_type = "html"`
           - `total_rows = len(parsed_records) + unparsed_rows`
           - `parsed_records = parsed_records`
           - `unparsed_rows = unparsed_rows`
           - `errors = errors`
           - `warnings = warnings`
       - Define convenience helper `parse_html_file(file_path: Union[Path, str], rules: Optional[SlaRulesConfig] = None) -> ExtractionResult` that reads file and invokes `parse_html_table`.
    2. In `core/parsers/__init__.py`, export `parse_html_table` and `parse_html_file`.

    AVOID: Crashing on malformed HTML, missing `<th>` tags, or nested tables.
    USE: Defensive BeautifulSoup parsing, `get_text(strip=True)`, `resolve_column_name`, and populated `ExtractionResult.warnings` for unexpected formats.
  </action>
  <verify>
    python -c "from core.parsers.html_parser import parse_html_table; res = parse_html_table('<html><body><table class=\"confluenceTable\"><tr><th>Issue Key</th><th>Summary</th><th>Assignee</th></tr><tr><td>PROJ-101</td><td>Fix auth crash</td><td>Platform</td></tr></table></body></html>'); assert len(res.parsed_records) == 1 and res.parsed_records[0].key == 'PROJ-101' and res.parsed_records[0].team == 'Platform'; print('HTML parser verification passed')"
  </verify>
  <done>
    `core/parsers/html_parser.py` parses Confluence and generic HTML tables into `ExtractionResult` containing `SlaRecord` models with canonical mappings and `raw_fields` preservation.
  </done>
</task>

<task type="auto">
  <name>Task 2: Implement Word DOCX table parser</name>
  <files>
    core/parsers/docx_parser.py
    core/parsers/__init__.py
  </files>
  <action>
    1. Create `core/parsers/docx_parser.py`:
       - Define `parse_docx_table(docx_source: Union[Path, str, bytes, BinaryIO], source_filename: str = "upload.docx", rules: Optional[SlaRulesConfig] = None) -> ExtractionResult`:
         - Loads document via `docx.Document(docx_source)` (wrapping `bytes` in `io.BytesIO` if passed as bytes).
         - Retrieves rules: `rules = rules or get_sla_rules()`.
         - Inspects `doc.tables`. If no tables exist, returns `ExtractionResult` with warning `"No tables found in document"`.
         - Iterates through all tables in the document:
           - Extracts header row (row 0). Handles merged cells in headers by deduplicating cell texts preserving column indices.
           - Resolves headers using `resolve_column_name(header, rules.column_mappings)`.
           - Checks if table contains ticket identifying column (`ticket_id` or key synonyms).
           - Iterates over data rows (row 1 to end):
             - Extracts cell texts (`cell.text.strip()`).
             - Skips rows where all cells are blank.
             - Handles merged data cells gracefully without raising IndexError.
             - Maps `ticket_id` -> `SlaRecord.key`. If key is empty, increments `unparsed_rows` and records warning.
             - Maps canonical fields: `summary`, `team`, `status`, `priority`.
             - Preserves unmapped table columns in `SlaRecord.raw_fields[header] = cell_text`.
             - Appends valid `SlaRecord` to `parsed_records`.
         - Assembles and returns `ExtractionResult`:
           - `source_filename = source_filename`
           - `file_type = "docx"`
           - `total_rows = len(parsed_records) + unparsed_rows`
           - `parsed_records = parsed_records`
           - `unparsed_rows = unparsed_rows`
           - `errors = errors`
           - `warnings = warnings`
       - Define convenience helper `parse_docx_file(file_path: Union[Path, str], rules: Optional[SlaRulesConfig] = None) -> ExtractionResult`.
    2. In `core/parsers/__init__.py`, export `parse_docx_table` and `parse_docx_file`.

    AVOID: Assuming a single table per document or crashing when encountering merged cells.
    USE: `python-docx` table iteration, `io.BytesIO` support for stream uploads, and `resolve_column_name` for header resolution.
  </action>
  <verify>
    python -c "import docx, io; doc = docx.Document(); t = doc.add_table(rows=2, cols=3); t.rows[0].cells[0].text='Key'; t.rows[0].cells[1].text='Summary'; t.rows[0].cells[2].text='Custom'; t.rows[1].cells[0].text='OPS-202'; t.rows[1].cells[1].text='Storage full'; t.rows[1].cells[2].text='ExtraVal'; buf = io.BytesIO(); doc.save(buf); buf.seek(0); from core.parsers.docx_parser import parse_docx_table; res = parse_docx_table(buf); assert len(res.parsed_records) == 1 and res.parsed_records[0].key == 'OPS-202' and res.parsed_records[0].raw_fields.get('Custom') == 'ExtraVal'; print('DOCX parser verification passed')"
  </verify>
  <done>
    `core/parsers/docx_parser.py` parses Word DOCX tables into `ExtractionResult` containing `SlaRecord` models, handling merged cells and stream/file inputs.
  </done>
</task>

<task type="auto">
  <name>Task 3: Implement comprehensive unit tests for HTML and DOCX parsers</name>
  <files>
    tests/test_parsers.py
  </files>
  <action>
    Create `tests/test_parsers.py` with comprehensive unit tests for both parsers:
    1. HTML Parser Tests:
       - Standard Confluence HTML table (`confluenceTable` class, `<th>` headers).
       - Alternate column synonyms ("Issue key", "Reported", "Assignee", "Urgency").
       - Dirty HTML: nested `<table>` tags inside a cell, non-breaking spaces `&nbsp;`, trailing line breaks.
       - Missing header row or table without ticket ID column (verifies warnings/unparsed rows tracking).
       - Document with multiple tables (one irrelevant summary table, one ticket table).
       - Completely empty table and table with blank rows.
       - Lossless retention of unmapped columns in `raw_fields`.
    2. DOCX Parser Tests:
       - Programmatically generated DOCX using `python-docx` in `io.BytesIO` with clean ticket table.
       - DOCX with merged cells in header and data rows.
       - DOCX with multiple tables.
       - DOCX document without tables (verifies safe return with warning).
       - Unmapped column preservation in `raw_fields`.
    3. Cross-Cutting ExtractionResult Tests:
       - Verifies `total_rows`, `parsed_records`, `unparsed_rows`, `errors`, `warnings`, and `source_filename`.

    AVOID: Depending on external static file fixtures on disk; generate HTML strings and in-memory `io.BytesIO` DOCX documents programmatically.
    USE: Pytest parameterization, fixtures, and strict assertions on `SlaRecord` fields and `ExtractionResult`.
  </action>
  <verify>
    pytest tests/test_parsers.py -v
  </verify>
  <done>
    `tests/test_parsers.py` contains comprehensive unit tests for HTML and DOCX parsers, all passing with zero errors.
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:
- [ ] `core/parsers/html_parser.py` and `core/parsers/docx_parser.py` are importable from `core.parsers`.
- [ ] HTML parser handles Confluence exports, nested tables, dirty data, and header synonyms.
- [ ] DOCX parser handles Word documents, merged cells, and byte stream inputs.
- [ ] Unmapped columns are faithfully retained in `SlaRecord.raw_fields`.
- [ ] All unit tests in `tests/test_parsers.py` pass cleanly.
</verification>

<success_criteria>
- [ ] All 3 tasks verified passing with runnable commands.
- [ ] Must-haves confirmed against REQ-02 and REQ-03.
- [ ] Unit tests pass via `pytest tests/test_parsers.py`.
</success_criteria>
