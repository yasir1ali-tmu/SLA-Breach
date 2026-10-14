"""Comprehensive unit tests for HTML/Confluence and DOCX table extraction parsers."""

from datetime import datetime, timezone
import io
from pathlib import Path
import docx
import pytest

from core.models.sla import ExtractionResult, SlaRecord
from core.parsers.docx_parser import parse_docx_file, parse_docx_table
from core.parsers.html_parser import parse_html_file, parse_html_table


# ==============================================================================
# HTML / Confluence Parser Tests
# ==============================================================================

def test_parse_html_standard_confluence():
    html = """
    <html>
      <body>
        <table class="confluenceTable">
          <thead>
            <tr class="confluenceTr">
              <th class="confluenceTh">Issue Key</th>
              <th class="confluenceTh">Summary</th>
              <th class="confluenceTh">Assignee</th>
              <th class="confluenceTh">Status</th>
              <th class="confluenceTh">Priority</th>
              <th class="confluenceTh">Created</th>
            </tr>
          </thead>
          <tbody>
            <tr class="confluenceTr">
              <td class="confluenceTd">PROJ-101</td>
              <td class="confluenceTd">Database connection timeout</td>
              <td class="confluenceTd">Infrastructure</td>
              <td class="confluenceTd">Open</td>
              <td class="confluenceTd">P1</td>
              <td class="confluenceTd">2026-10-10 09:30:00</td>
            </tr>
            <tr class="confluenceTr">
              <td class="confluenceTd">PROJ-102</td>
              <td class="confluenceTd">UI button alignment</td>
              <td class="confluenceTd">Frontend</td>
              <td class="confluenceTd">Resolved</td>
              <td class="confluenceTd">P3</td>
              <td class="confluenceTd">2026-10-11</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """
    res = parse_html_table(html, source_filename="export.html")

    assert isinstance(res, ExtractionResult)
    assert res.file_type == "html"
    assert res.source_filename == "export.html"
    assert res.total_rows == 2
    assert len(res.parsed_records) == 2
    assert res.unparsed_rows == 0
    assert len(res.errors) == 0

    rec1 = res.parsed_records[0]
    assert rec1.key == "PROJ-101"
    assert rec1.summary == "Database connection timeout"
    assert rec1.team == "Infrastructure"
    assert rec1.status == "Open"
    assert rec1.priority == "P1"
    assert isinstance(rec1.created_date, datetime)
    assert rec1.created_date.year == 2026
    assert rec1.created_date.month == 10
    assert rec1.created_date.day == 10

    rec2 = res.parsed_records[1]
    assert rec2.key == "PROJ-102"
    assert rec2.summary == "UI button alignment"
    assert rec2.team == "Frontend"
    assert rec2.status == "Resolved"
    assert rec2.priority == "P3"
    assert isinstance(rec2.created_date, datetime)


def test_parse_html_column_synonyms():
    html = """
    <table>
      <tr>
        <td>Ticket</td>
        <td>Title</td>
        <td>Owner</td>
        <td>State</td>
        <td>Urgency</td>
        <td>Reported Date</td>
        <td>Target Resolution Date</td>
        <td>Closed Date</td>
      </tr>
      <tr>
        <td>INC-900</td>
        <td>Network latency burst</td>
        <td>NetworkOps</td>
        <td>In Progress</td>
        <td>Major</td>
        <td>2026-10-12 14:00</td>
        <td>2026-10-17 14:00</td>
        <td>2026-10-15 11:20</td>
      </tr>
    </table>
    """
    res = parse_html_table(html)
    assert len(res.parsed_records) == 1
    rec = res.parsed_records[0]
    assert rec.key == "INC-900"
    assert rec.summary == "Network latency burst"
    assert rec.team == "NetworkOps"
    assert rec.status == "In Progress"
    assert rec.priority == "Major"
    assert isinstance(rec.created_date, datetime)
    assert isinstance(rec.due_date, datetime)
    assert isinstance(rec.resolved_date, datetime)


def test_parse_html_dirty_content_and_nested_tables():
    html = """
    <table>
      <tr>
        <th>Key</th>
        <th>Summary</th>
        <th>Assignee</th>
      </tr>
      <tr>
        <td>&nbsp;&nbsp;SEC-550&nbsp;</td>
        <td>
          Memory leak in gateway
          <table class="innerTable">
            <tr><td>Nested debug trace: PID 4510</td></tr>
          </table>
        </td>
        <td>Security&nbsp;Team\n\n\t</td>
      </tr>
    </table>
    """
    res = parse_html_table(html)
    assert len(res.parsed_records) == 1
    rec = res.parsed_records[0]
    assert rec.key == "SEC-550"
    assert "Memory leak in gateway" in rec.summary
    assert "PID 4510" in rec.summary
    assert rec.team == "Security Team"


def test_parse_html_unmapped_columns_in_raw_fields():
    html = """
    <table>
      <tr>
        <th>Key</th>
        <th>Summary</th>
        <th>Cost Center</th>
        <th>Release Tag</th>
      </tr>
      <tr>
        <td>DEV-88</td>
        <td>API Gateway migration</td>
        <td>CC-9901</td>
        <td>v3.2.0-rc1</td>
      </tr>
    </table>
    """
    res = parse_html_table(html)
    assert len(res.parsed_records) == 1
    rec = res.parsed_records[0]
    assert rec.key == "DEV-88"
    assert rec.summary == "API Gateway migration"
    assert rec.raw_fields.get("Cost Center") == "CC-9901"
    assert rec.raw_fields.get("Release Tag") == "v3.2.0-rc1"


def test_parse_html_missing_key_tracks_unparsed():
    html = """
    <table>
      <tr>
        <th>Key</th>
        <th>Summary</th>
      </tr>
      <tr>
        <td></td>
        <td>Missing issue key row</td>
      </tr>
      <tr>
        <td>VALID-1</td>
        <td>Good ticket</td>
      </tr>
    </table>
    """
    res = parse_html_table(html)
    assert res.total_rows == 2
    assert len(res.parsed_records) == 1
    assert res.unparsed_rows == 1
    assert any("Blank or missing ticket identifier" in w for w in res.warnings)
    assert res.parsed_records[0].key == "VALID-1"


def test_parse_html_multiple_tables():
    html = """
    <html>
      <body>
        <table id="metaTable">
          <tr><th>Report Title</th><th>Generated At</th></tr>
          <tr><td>Weekly SLA Snapshot</td><td>2026-10-14</td></tr>
        </table>
        <table id="ticketsTable">
          <tr><th>Key</th><th>Summary</th><th>Assignee</th></tr>
          <tr><td>OPS-100</td><td>Disk alert</td><td>Storage</td></tr>
        </table>
      </body>
    </html>
    """
    res = parse_html_table(html)
    assert len(res.parsed_records) == 1
    assert res.parsed_records[0].key == "OPS-100"
    assert res.parsed_records[0].summary == "Disk alert"


def test_parse_html_empty_and_blank_rows():
    # Empty content
    res_empty = parse_html_table("")
    assert res_empty.total_rows == 0
    assert any("empty" in w.lower() for w in res_empty.warnings)

    # Document without tables
    res_no_tables = parse_html_table("<html><body><p>Hello World</p></body></html>")
    assert res_no_tables.total_rows == 0
    assert any("No table elements found" in w for w in res_no_tables.warnings)

    # Table with blank row
    html_blank = """
    <table>
      <tr><th>Key</th><th>Summary</th></tr>
      <tr><td>   </td><td>&nbsp;</td></tr>
      <tr><td>KEY-1</td><td>Active</td></tr>
    </table>
    """
    res_blank = parse_html_table(html_blank)
    assert len(res_blank.parsed_records) == 1
    assert res_blank.parsed_records[0].key == "KEY-1"


def test_parse_html_file_helper(tmp_path: Path):
    file_path = tmp_path / "tickets.html"
    file_path.write_text(
        "<table><tr><th>Key</th><th>Summary</th></tr><tr><td>FILE-1</td><td>From file</td></tr></table>",
        encoding="utf-8",
    )

    res = parse_html_file(file_path)
    assert len(res.parsed_records) == 1
    assert res.parsed_records[0].key == "FILE-1"
    assert res.source_filename == "tickets.html"

    # Non-existent file
    missing_res = parse_html_file(tmp_path / "missing.html")
    assert len(missing_res.errors) == 1
    assert "File not found" in missing_res.errors[0]


# ==============================================================================
# DOCX Parser Tests
# ==============================================================================

def test_parse_docx_standard_table():
    doc = docx.Document()
    t = doc.add_table(rows=3, cols=6)

    headers = ["Key", "Summary", "Assignee", "Status", "Priority", "Created"]
    for i, h in enumerate(headers):
        t.rows[0].cells[i].text = h

    row1 = ["DOC-1", "Upgrade python dependencies", "DevOps", "In Progress", "P2", "2026-10-08"]
    for i, val in enumerate(row1):
        t.rows[1].cells[i].text = val

    row2 = ["DOC-2", "Add unit tests", "QA", "Closed", "P4", "2026-10-09"]
    for i, val in enumerate(row2):
        t.rows[2].cells[i].text = val

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    res = parse_docx_table(buf, source_filename="sla_report.docx")
    assert res.file_type == "docx"
    assert res.source_filename == "sla_report.docx"
    assert res.total_rows == 2
    assert len(res.parsed_records) == 2
    assert res.parsed_records[0].key == "DOC-1"
    assert res.parsed_records[0].team == "DevOps"
    assert res.parsed_records[0].priority == "P2"
    assert res.parsed_records[1].key == "DOC-2"
    assert res.parsed_records[1].team == "QA"


def test_parse_docx_merged_cells():
    doc = docx.Document()
    t = doc.add_table(rows=2, cols=4)

    # Merge header cells 0 and 1
    t.rows[0].cells[0].text = "Key"
    t.rows[0].cells[1].text = "Key"
    t.rows[0].cells[2].text = "Summary"
    t.rows[0].cells[3].text = "Owner"

    # Merge data cells 2 and 3
    t.rows[1].cells[0].text = "MERGE-10"
    t.rows[1].cells[1].text = "MERGE-10"
    t.rows[1].cells[2].text = "Merged description across cells"
    t.rows[1].cells[3].text = "Merged description across cells"

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    res = parse_docx_table(buf)
    assert len(res.parsed_records) == 1
    assert res.parsed_records[0].key == "MERGE-10"


def test_parse_docx_multiple_tables():
    doc = docx.Document()

    # Table 1: metadata
    t1 = doc.add_table(rows=2, cols=2)
    t1.rows[0].cells[0].text = "Department"
    t1.rows[0].cells[1].text = "Quarter"
    t1.rows[1].cells[0].text = "Engineering"
    t1.rows[1].cells[1].text = "Q4"

    # Table 2: tickets
    t2 = doc.add_table(rows=2, cols=3)
    t2.rows[0].cells[0].text = "Ticket ID"
    t2.rows[0].cells[1].text = "Description"
    t2.rows[0].cells[2].text = "Team"
    t2.rows[1].cells[0].text = "ENG-44"
    t2.rows[1].cells[1].text = "CI pipeline failure"
    t2.rows[1].cells[2].text = "Infra"

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    res = parse_docx_table(buf)
    assert len(res.parsed_records) == 1
    assert res.parsed_records[0].key == "ENG-44"
    assert res.parsed_records[0].summary == "CI pipeline failure"
    assert res.parsed_records[0].team == "Infra"


def test_parse_docx_no_tables():
    doc = docx.Document()
    doc.add_paragraph("Just text without any tables.")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    res = parse_docx_table(buf)
    assert res.total_rows == 0
    assert len(res.parsed_records) == 0
    assert any("No tables found" in w for w in res.warnings)


def test_parse_docx_unmapped_columns_and_blank_rows():
    doc = docx.Document()
    t = doc.add_table(rows=3, cols=3)
    t.rows[0].cells[0].text = "Key"
    t.rows[0].cells[1].text = "Summary"
    t.rows[0].cells[2].text = "Custom Metadata"

    # Blank row
    t.rows[1].cells[0].text = ""
    t.rows[1].cells[1].text = ""
    t.rows[1].cells[2].text = ""

    # Valid row
    t.rows[2].cells[0].text = "CUST-99"
    t.rows[2].cells[1].text = "Test custom data"
    t.rows[2].cells[2].text = "Special-Tag-XYZ"

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    res = parse_docx_table(buf)
    assert len(res.parsed_records) == 1
    assert res.parsed_records[0].key == "CUST-99"
    assert res.parsed_records[0].raw_fields.get("Custom Metadata") == "Special-Tag-XYZ"


def test_parse_docx_file_helper(tmp_path: Path):
    doc = docx.Document()
    t = doc.add_table(rows=2, cols=2)
    t.rows[0].cells[0].text = "Key"
    t.rows[0].cells[1].text = "Summary"
    t.rows[1].cells[0].text = "DOCFILE-1"
    t.rows[1].cells[1].text = "From docx file"

    file_path = tmp_path / "sample.docx"
    doc.save(str(file_path))

    res = parse_docx_file(file_path)
    assert len(res.parsed_records) == 1
    assert res.parsed_records[0].key == "DOCFILE-1"

    # Missing file
    missing = parse_docx_file(tmp_path / "nonexistent.docx")
    assert len(missing.errors) == 1
    assert "File not found" in missing.errors[0]


def test_parse_docx_corrupt_stream():
    bad_bytes = b"not a valid zip or docx content"
    res = parse_docx_table(bad_bytes)
    assert len(res.errors) == 1
    assert "Failed to open DOCX document" in res.errors[0]


# ==============================================================================
# Cross-Cutting ExtractionResult Tests
# ==============================================================================

def test_extraction_result_metadata():
    html = "<table><tr><th>Key</th><th>Summary</th></tr><tr><td>K-1</td><td>S-1</td></tr></table>"
    res = parse_html_table(html, source_filename="batch.html")

    assert res.source_filename == "batch.html"
    assert res.file_type == "html"
    assert isinstance(res.extracted_at, datetime)
    assert res.total_rows == len(res.parsed_records) + res.unparsed_rows
    assert res.total_rows == 1
