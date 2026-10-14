"""Confluence and generic HTML table extraction parser."""

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from bs4 import BeautifulSoup

from config.settings import SlaRulesConfig, get_sla_rules, resolve_column_name
from core.models.sla import ExtractionResult, SlaRecord


def clean_cell_text(text: Optional[str]) -> str:
    """Normalize extracted text by cleaning non-breaking spaces and redundant whitespace."""
    if not text:
        return ""
    cleaned = text.replace("\xa0", " ").replace("\u200b", " ")
    cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def parse_date_value(
    val: str, formats: List[str], default_tz: str = "UTC"
) -> Optional[datetime]:
    """Attempt to parse date strings via ISO format or configured format patterns."""
    if not val or not val.strip():
        return None
    val_str = val.strip()

    # Try ISO format parsing
    try:
        clean_iso = val_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_iso)
        if dt.tzinfo is None and default_tz.upper() == "UTC":
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass

    # Try configured format templates
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            if dt.tzinfo is None and default_tz.upper() == "UTC":
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            continue

    return None


def _find_header_row(
    rows: List[Any], mappings: Any
) -> Tuple[Optional[int], List[Tuple[str, Optional[str]]]]:
    """Inspect the first few rows of a table to locate the header row containing ticket_id."""
    max_scan = min(5, len(rows))
    for r_idx in range(max_scan):
        row = rows[r_idx]
        cells = [c for c in row.find_all(["th", "td"]) if c.find_parent("tr") == row]
        if not cells:
            continue

        candidate_headers: List[Tuple[str, Optional[str]]] = []
        has_ticket_id = False

        for idx, cell in enumerate(cells):
            raw_title = clean_cell_text(cell.get_text(separator=" ", strip=True))
            header_name = raw_title if raw_title else f"Column_{idx + 1}"
            canonical = resolve_column_name(header_name, mappings)
            if canonical == "ticket_id":
                has_ticket_id = True
            candidate_headers.append((header_name, canonical))

        if has_ticket_id:
            return r_idx, candidate_headers

    # Fallback: if no ticket_id found, check if first row with <th> exists
    for r_idx in range(max_scan):
        row = rows[r_idx]
        th_cells = [c for c in row.find_all("th") if c.find_parent("tr") == row]
        if th_cells:
            candidate_headers = []
            for idx, cell in enumerate(th_cells):
                raw_title = clean_cell_text(cell.get_text(separator=" ", strip=True))
                header_name = raw_title if raw_title else f"Column_{idx + 1}"
                canonical = resolve_column_name(header_name, mappings)
                candidate_headers.append((header_name, canonical))
            return r_idx, candidate_headers

    return None, []


def parse_html_table(
    html_content: Union[str, bytes],
    source_filename: str = "upload.html",
    rules: Optional[SlaRulesConfig] = None,
) -> ExtractionResult:
    """Parse Confluence or generic HTML tables into structured SlaRecord models.

    Args:
        html_content: HTML content as string or bytes.
        source_filename: Name of the uploaded or source file.
        rules: Optional custom SLA rules configuration. Uses default if None.

    Returns:
        ExtractionResult containing parsed SlaRecords, row counts, warnings, and errors.
    """
    rules = rules or get_sla_rules()
    warnings: List[str] = []
    errors: List[str] = []
    parsed_records: List[SlaRecord] = []
    unparsed_rows = 0

    if not html_content:
        warnings.append("HTML content is empty")
        return ExtractionResult(
            source_filename=source_filename,
            file_type="html",
            total_rows=0,
            parsed_records=[],
            unparsed_rows=0,
            warnings=warnings,
            errors=errors,
        )

    # Convert bytes to string if needed
    if isinstance(html_content, bytes):
        try:
            html_text = html_content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                html_text = html_content.decode("latin-1")
            except Exception as exc:
                errors.append(f"Failed to decode byte stream: {exc}")
                return ExtractionResult(
                    source_filename=source_filename,
                    file_type="html",
                    total_rows=0,
                    parsed_records=[],
                    unparsed_rows=0,
                    warnings=warnings,
                    errors=errors,
                )
    else:
        html_text = html_content

    # Parse HTML with lxml, falling back to html.parser
    try:
        soup = BeautifulSoup(html_text, "lxml")
    except Exception:
        soup = BeautifulSoup(html_text, "html.parser")

    tables = soup.find_all("table")
    if not tables:
        warnings.append("No table elements found in HTML document")
        return ExtractionResult(
            source_filename=source_filename,
            file_type="html",
            total_rows=0,
            parsed_records=[],
            unparsed_rows=0,
            warnings=warnings,
            errors=errors,
        )

    ticket_tables_found = 0

    for table_idx, table in enumerate(tables):
        # Exclude inner nested tables from outer table row discovery
        rows = [tr for tr in table.find_all("tr") if tr.find_parent("table") == table]
        if not rows:
            continue

        header_idx, headers = _find_header_row(rows, rules.column_mappings)
        has_ticket_key = any(canon == "ticket_id" for _, canon in headers)

        if not has_ticket_key:
            # Table does not have ticket_id column; ignore or note
            continue

        ticket_tables_found += 1
        data_rows = rows[header_idx + 1 :] if header_idx is not None else []

        for row_pos, tr in enumerate(data_rows, start=header_idx + 2 if header_idx is not None else 1):
            cells = [c for c in tr.find_all(["td", "th"]) if c.find_parent("tr") == tr]
            if not cells:
                continue

            # Extract cell texts
            cell_texts = [clean_cell_text(c.get_text(separator=" ", strip=True)) for c in cells]

            # Skip completely empty rows
            if not any(cell_texts):
                continue

            # Check if this row is a duplicate header row in paginated tables
            if all(
                clean_cell_text(cells[i].get_text(separator=" ", strip=True)) == headers[i][0]
                for i in range(min(len(cells), len(headers)))
            ):
                continue

            row_data: Dict[str, Any] = {}
            raw_fields: Dict[str, Any] = {}

            for col_idx, (orig_header, canon_field) in enumerate(headers):
                cell_val = cell_texts[col_idx] if col_idx < len(cell_texts) else ""

                if canon_field == "ticket_id":
                    row_data["key"] = cell_val
                elif canon_field == "summary":
                    row_data["summary"] = cell_val or None
                elif canon_field == "team":
                    row_data["team"] = cell_val or None
                elif canon_field == "status":
                    row_data["status"] = cell_val or None
                elif canon_field == "priority":
                    row_data["priority"] = cell_val or None
                elif canon_field in ("created_date", "resolved_date", "due_date"):
                    dt = parse_date_value(
                        cell_val,
                        rules.date_parsing.formats,
                        rules.date_parsing.default_timezone,
                    )
                    row_data[canon_field] = dt
                    if dt is None and cell_val:
                        raw_fields[orig_header] = cell_val
                else:
                    # Unmapped column preserved in raw_fields
                    raw_fields[orig_header] = cell_val

            # Preserve any extra cells beyond known header count
            if len(cell_texts) > len(headers):
                for extra_idx in range(len(headers), len(cell_texts)):
                    raw_fields[f"Column_{extra_idx + 1}"] = cell_texts[extra_idx]

            ticket_key = row_data.get("key", "").strip()
            if not ticket_key:
                unparsed_rows += 1
                warnings.append(
                    f"Table {table_idx + 1}, Row {row_pos}: Blank or missing ticket identifier, skipped."
                )
                continue

            record = SlaRecord(
                key=ticket_key,
                summary=row_data.get("summary"),
                team=row_data.get("team"),
                status=row_data.get("status"),
                priority=row_data.get("priority"),
                created_date=row_data.get("created_date"),
                resolved_date=row_data.get("resolved_date"),
                due_date=row_data.get("due_date"),
                raw_fields=raw_fields,
            )
            parsed_records.append(record)

    if ticket_tables_found == 0:
        warnings.append("No table containing a recognized ticket identifier column ('ticket_id') was found")

    total_rows = len(parsed_records) + unparsed_rows

    return ExtractionResult(
        source_filename=source_filename,
        file_type="html",
        total_rows=total_rows,
        parsed_records=parsed_records,
        unparsed_rows=unparsed_rows,
        errors=errors,
        warnings=warnings,
    )


def parse_html_file(
    file_path: Union[Path, str],
    rules: Optional[SlaRulesConfig] = None,
) -> ExtractionResult:
    """Read an HTML file from disk and parse tables into ExtractionResult.

    Args:
        file_path: Path to the HTML file.
        rules: Optional custom SLA rules configuration.

    Returns:
        ExtractionResult containing parsed records or file read errors.
    """
    path = Path(file_path)
    if not path.is_file():
        return ExtractionResult(
            source_filename=path.name,
            file_type="html",
            total_rows=0,
            parsed_records=[],
            unparsed_rows=0,
            errors=[f"File not found: {path}"],
            warnings=[],
        )

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as exc:
        return ExtractionResult(
            source_filename=path.name,
            file_type="html",
            total_rows=0,
            parsed_records=[],
            unparsed_rows=0,
            errors=[f"Failed to read file {path}: {exc}"],
            warnings=[],
        )

    return parse_html_table(content, source_filename=path.name, rules=rules)
