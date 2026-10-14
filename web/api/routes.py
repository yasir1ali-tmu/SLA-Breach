"""REST API endpoints for health status, rules configuration, and file ingestion."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, UploadFile

from config.settings import get_settings, get_sla_rules
from core.analytics.metrics import compute_analytics_payload
from core.parsers.docx_parser import parse_docx_table
from core.parsers.html_parser import parse_html_table
from core.sla.engine import SlaEngine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", summary="Service health status")
async def health_check() -> Dict[str, Any]:
    """Return health status, service metadata, and UTC timestamp."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/rules", summary="Active SLA configuration and rules")
async def get_rules() -> Dict[str, Any]:
    """Return active SLA thresholds, severity rules, column aliases, and upload constraints."""
    rules = get_sla_rules()
    settings = get_settings()
    return {
        "sla_thresholds": rules.sla_thresholds.model_dump(),
        "severity_rules": rules.severity_rules.model_dump(),
        "column_mappings": rules.column_mappings.model_dump(),
        "allowed_extensions": settings.allowed_extensions,
        "max_upload_size_mb": settings.max_upload_size_mb,
    }


@router.post("/upload", summary="Upload export file and compute SLA metrics")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Accept and parse Confluence HTML or Word DOCX ticket tables, calculating SLA compliance.

    Validates file extension and size, extracts tabular ticket records, evaluates SLA
    metrics (elapsed days, overdue days, breach status, severity), and aggregates summary KPIs.

    Args:
        file: Uploaded multipart file stream.

    Returns:
        JSON response with file metadata, warnings, errors, aggregated KPIs, and evaluated records.

    Raises:
        HTTPException 400: If file extension is unsupported or file is empty (0 bytes).
        HTTPException 413: If file size exceeds configured max_upload_size_mb.
    """
    settings = get_settings()
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()

    # Validate file extension
    if ext not in settings.allowed_extensions:
        allowed = ", ".join(settings.allowed_extensions)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {allowed}",
        )

    # Read uploaded content asynchronously
    content = await file.read()

    # Validate non-empty file
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty (0 bytes).",
        )

    # Validate maximum file size
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum upload limit of {settings.max_upload_size_mb} MB.",
        )

    # Parse table records based on file type
    if ext in [".html", ".htm"]:
        html_text = content.decode("utf-8", errors="replace")
        extraction_result = parse_html_table(html_text, source_filename=filename)
    elif ext == ".docx":
        extraction_result = parse_docx_table(content, source_filename=filename)
    else:
        # Fallback safeguard
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'.",
        )

    # Compute SLA compliance metrics
    engine = SlaEngine()
    engine.process_extraction_result(extraction_result)
    summary_metrics = engine.calculate_summary_metrics(extraction_result.parsed_records)
    analytics = compute_analytics_payload(extraction_result.parsed_records)

    return {
        "source_filename": filename,
        "file_type": extraction_result.file_type,
        "extracted_at": extraction_result.extracted_at.isoformat(),
        "total_rows": extraction_result.total_rows,
        "parsed_count": len(extraction_result.parsed_records),
        "unparsed_rows": extraction_result.unparsed_rows,
        "errors": extraction_result.errors,
        "warnings": extraction_result.warnings,
        "metrics": summary_metrics.model_dump(mode="json"),
        "analytics": analytics,
        "records": [
            r.model_dump(mode="json") for r in extraction_result.parsed_records
        ],
    }
