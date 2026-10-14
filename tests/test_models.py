"""Unit tests for SLA Pydantic data models."""

from datetime import datetime, timezone
import json
import pytest
from pydantic import ValidationError

from core.models import (
    ExtractionResult,
    SeverityLevel,
    SlaRecord,
    SlaSummaryMetrics,
)


def test_severity_level_values_and_properties():
    """Verify SeverityLevel enum values and UI helper properties."""
    assert SeverityLevel.OK.value == "OK"
    assert SeverityLevel.WARNING.value == "WARNING"
    assert SeverityLevel.CRITICAL.value == "CRITICAL"
    assert SeverityLevel.BREACHED.value == "BREACHED"

    for level in SeverityLevel:
        assert isinstance(level.badge_class, str)
        assert len(level.badge_class) > 0
        assert isinstance(level.display_name, str)
        assert len(level.display_name) > 0


def test_sla_record_minimal_instantiation():
    """Test SlaRecord creation with only required fields."""
    record = SlaRecord(key="PROJ-101")
    assert record.key == "PROJ-101"
    assert record.id is not None
    assert len(record.id) > 0
    assert record.is_breached is False
    assert record.severity == SeverityLevel.OK
    assert record.raw_fields == {}
    assert record.summary is None
    assert record.team is None


def test_sla_record_full_instantiation():
    """Test SlaRecord creation with all fields populated."""
    now = datetime.now(timezone.utc)
    record = SlaRecord(
        id="custom-id-123",
        key="OPS-999",
        summary="Service degradation in region us-east",
        team="Platform Eng",
        status="Closed",
        priority="P1",
        created_date=now,
        resolved_date=now,
        due_date=now,
        sla_target_days=2.0,
        elapsed_days=4.5,
        overdue_days=2.5,
        is_breached=True,
        severity=SeverityLevel.BREACHED,
        raw_fields={"Custom Field 1": "value1", "Score": 95},
    )

    assert record.id == "custom-id-123"
    assert record.key == "OPS-999"
    assert record.summary == "Service degradation in region us-east"
    assert record.team == "Platform Eng"
    assert record.status == "Closed"
    assert record.priority == "P1"
    assert record.created_date == now
    assert record.resolved_date == now
    assert record.due_date == now
    assert record.sla_target_days == 2.0
    assert record.elapsed_days == 4.5
    assert record.overdue_days == 2.5
    assert record.is_breached is True
    assert record.severity == SeverityLevel.BREACHED
    assert record.raw_fields == {"Custom Field 1": "value1", "Score": 95}


def test_sla_record_serialization():
    """Test serialization of SlaRecord to dict and JSON."""
    record = SlaRecord(
        key="SEC-404",
        summary="Vulnerability scan finding",
        raw_fields={"unmapped_col": 1234},
    )
    dumped_dict = record.model_dump()
    assert isinstance(dumped_dict, dict)
    assert dumped_dict["key"] == "SEC-404"
    assert dumped_dict["raw_fields"]["unmapped_col"] == 1234

    dumped_json = record.model_dump_json()
    assert isinstance(dumped_json, str)
    parsed = json.loads(dumped_json)
    assert parsed["key"] == "SEC-404"
    assert parsed["raw_fields"]["unmapped_col"] == 1234


def test_sla_record_missing_key_validation():
    """Verify that omitting key raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        SlaRecord()  # type: ignore
    errors = exc_info.value.errors()
    field_names = [e["loc"][0] for e in errors]
    assert "key" in field_names


def test_extraction_result_model():
    """Verify ExtractionResult default values and record tracking."""
    result = ExtractionResult(
        source_filename="export.html",
        file_type="html",
    )
    assert result.source_filename == "export.html"
    assert result.file_type == "html"
    assert result.total_rows == 0
    assert len(result.parsed_records) == 0
    assert len(result.errors) == 0
    assert len(result.warnings) == 0
    assert result.extracted_at is not None

    record = SlaRecord(key="TEST-1")
    result.parsed_records.append(record)
    result.total_rows = 1
    assert len(result.parsed_records) == 1
    assert result.parsed_records[0].key == "TEST-1"


def test_sla_summary_metrics_model():
    """Verify SlaSummaryMetrics default values and aggregation storage."""
    metrics = SlaSummaryMetrics(
        total_records=100,
        breached_count=20,
        warning_count=15,
        compliant_count=65,
        breach_rate_pct=20.0,
        avg_overdue_days=3.4,
        max_overdue_days=12.0,
        by_severity={"BREACHED": 20, "WARNING": 15, "OK": 65},
        by_team={"Team A": {"breached": 5, "total": 25}},
    )
    assert metrics.total_records == 100
    assert metrics.breached_count == 20
    assert metrics.breach_rate_pct == 20.0
    assert metrics.by_severity["BREACHED"] == 20
    assert metrics.by_team["Team A"]["total"] == 25

    dumped = metrics.model_dump()
    assert dumped["total_records"] == 100
    assert dumped["by_severity"]["WARNING"] == 15
