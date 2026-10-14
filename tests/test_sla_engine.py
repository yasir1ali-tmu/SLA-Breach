"""Comprehensive unit tests for the SLA calculation engine, date parser, and severity evaluator."""

from datetime import datetime, timedelta, timezone
import pytest

from config.settings import SeverityRulesConfig, SlaRulesConfig, SlaThresholdsConfig
from core.models.sla import (
    ExtractionResult,
    SeverityLevel,
    SlaRecord,
    SlaSummaryMetrics,
)
from core.parsers.date_parser import parse_date_safe, parse_datetime
from core.sla.engine import SlaEngine
from core.sla.severity import evaluate_severity


# ==============================================================================
# Date Parser Tests
# ==============================================================================

class TestDateParser:
    """Tests for resilient multi-format date parser."""

    def test_parse_iso_formats(self):
        """Verify standard ISO 8601 date and datetime strings."""
        dt1 = parse_datetime("2024-01-15 10:30:00")
        assert dt1 is not None
        assert dt1.tzinfo == timezone.utc
        assert dt1.year == 2024 and dt1.month == 1 and dt1.day == 15
        assert dt1.hour == 10 and dt1.minute == 30 and dt1.second == 0

        dt2 = parse_datetime("2024-01-15")
        assert dt2 is not None
        assert dt2.tzinfo == timezone.utc
        assert dt2.year == 2024 and dt2.month == 1 and dt2.day == 15

        dt3 = parse_datetime("2024-01-15T10:30:00Z")
        assert dt3 is not None
        assert dt3.tzinfo == timezone.utc
        assert dt3.hour == 10

        dt4 = parse_datetime("2024-01-15T12:30:00+02:00")
        assert dt4 is not None
        assert dt4.tzinfo == timezone.utc
        assert dt4.hour == 10  # 12:30+02:00 == 10:30 UTC

    def test_parse_slash_and_textual_formats(self):
        """Verify date formats with slash separators, month abbreviations, and AM/PM."""
        dt1 = parse_datetime("15/Jan/24 10:30 AM")
        assert dt1 is not None
        assert dt1.year == 2024 and dt1.month == 1 and dt1.day == 15
        assert dt1.hour == 10 and dt1.minute == 30

        # Case variations in month and am/pm
        dt2 = parse_datetime("15/jan/24 02:30 pm")
        assert dt2 is not None
        assert dt2.hour == 14 and dt2.minute == 30

        dt3 = parse_datetime("Jan 15, 2024 10:30 AM")
        assert dt3 is not None
        assert dt3.year == 2024 and dt3.month == 1 and dt3.day == 15

        dt4 = parse_datetime("15-Jan-2024")
        assert dt4 is not None
        assert dt4.year == 2024 and dt4.month == 1 and dt4.day == 15

    def test_parse_eu_us_numeric_formats(self):
        """Verify numeric EU (%d/%m/%Y) and US (%m/%d/%Y) date patterns."""
        dt1 = parse_datetime("15/01/2024 14:30:00")
        assert dt1 is not None
        assert dt1.day == 15 and dt1.month == 1 and dt1.year == 2024

        dt2 = parse_datetime("01/15/2024 02:30:00 PM")
        assert dt2 is not None
        assert dt2.day == 15 and dt2.month == 1 and dt2.year == 2024

        dt3 = parse_datetime("15/01/2024")
        assert dt3 is not None
        assert dt3.day == 15 and dt3.month == 1

        dt4 = parse_datetime("01/15/2024")
        assert dt4 is not None
        assert dt4.day == 15 and dt4.month == 1

    def test_parse_resilience_and_dirty_strings(self):
        """Verify handling of whitespace, quotes, and non-breaking spaces."""
        dt1 = parse_datetime("  2024-05-10 14:30:00  ")
        assert dt1 is not None and dt1.day == 10

        dt2 = parse_datetime("2024-05-10\xa014:30:00")
        assert dt2 is not None and dt2.day == 10

        dt3 = parse_datetime("'2024-05-10 14:30:00'")
        assert dt3 is not None and dt3.day == 10

        dt4 = parse_datetime('"2024-05-10"')
        assert dt4 is not None and dt4.day == 10

        dt5 = parse_datetime("15/Jan/24   10:30  AM")
        assert dt5 is not None and dt5.day == 15

    def test_parse_invalid_and_empty_inputs(self):
        """Verify non-throwing safe return of None on invalid inputs."""
        assert parse_datetime(None) is None
        assert parse_datetime("") is None
        assert parse_datetime("   ") is None
        assert parse_datetime("not-a-valid-date") is None
        assert parse_datetime("2024-99-99") is None
        assert parse_datetime(12345) is None
        assert parse_date_safe("completely-invalid") is None

    def test_parse_strict_mode(self):
        """Verify strict=True raises ValueError on unparseable input."""
        with pytest.raises(ValueError, match="Unable to parse"):
            parse_datetime("invalid-date", strict=True)

        with pytest.raises(ValueError, match="Cannot parse empty"):
            parse_datetime("   ", strict=True)

        with pytest.raises(ValueError, match="Cannot parse None"):
            parse_datetime(None, strict=True)

    def test_parse_existing_datetime_objects(self):
        """Verify existing naive and aware datetimes are converted to UTC aware datetimes."""
        naive = datetime(2024, 6, 1, 12, 0, 0)
        aware = parse_datetime(naive)
        assert aware.tzinfo == timezone.utc
        assert aware.year == 2024 and aware.hour == 12

        # Aware datetime with +04:00 offset
        tz_plus_4 = timezone(timedelta(hours=4))
        offset_dt = datetime(2024, 6, 1, 16, 0, 0, tzinfo=tz_plus_4)
        converted = parse_datetime(offset_dt)
        assert converted.tzinfo == timezone.utc
        assert converted.hour == 12  # 16:00+04:00 == 12:00 UTC


# ==============================================================================
# Severity Evaluator Tests
# ==============================================================================

class TestSeverityEvaluator:
    """Tests for breach severity categorization and precedence rules."""

    def test_severity_compliant_ok(self):
        """Elapsed < 80% of target and 0 overdue days is OK."""
        # 2.0 days elapsed out of 5.0 target = 40%
        sev = evaluate_severity(elapsed_days=2.0, target_days=5.0, overdue_days=0.0)
        assert sev == SeverityLevel.OK

        # 0.0 days elapsed is OK
        sev_zero = evaluate_severity(elapsed_days=0.0, target_days=5.0, overdue_days=0.0)
        assert sev_zero == SeverityLevel.OK

    def test_severity_warning(self):
        """Elapsed >= 80% and overdue == 0.0 triggers WARNING."""
        # Exactly 80%
        sev_80 = evaluate_severity(elapsed_days=4.0, target_days=5.0, overdue_days=0.0)
        assert sev_80 == SeverityLevel.WARNING

        # 90%
        sev_90 = evaluate_severity(elapsed_days=4.5, target_days=5.0, overdue_days=0.0)
        assert sev_90 == SeverityLevel.WARNING

        # 100% elapsed but overdue <= 0.0
        sev_100 = evaluate_severity(elapsed_days=5.0, target_days=5.0, overdue_days=0.0)
        assert sev_100 == SeverityLevel.WARNING

    def test_severity_breached(self):
        """Overdue > 0.0 and <= 3.0 triggers BREACHED."""
        sev1 = evaluate_severity(elapsed_days=5.1, target_days=5.0, overdue_days=0.1)
        assert sev1 == SeverityLevel.BREACHED

        sev2 = evaluate_severity(elapsed_days=7.0, target_days=5.0, overdue_days=2.0)
        assert sev2 == SeverityLevel.BREACHED

        # Boundary at critical cutoff (exactly 3.0 days overdue)
        sev3 = evaluate_severity(elapsed_days=8.0, target_days=5.0, overdue_days=3.0)
        assert sev3 == SeverityLevel.BREACHED

    def test_severity_critical(self):
        """Overdue > 3.0 triggers CRITICAL."""
        sev1 = evaluate_severity(elapsed_days=8.1, target_days=5.0, overdue_days=3.1)
        assert sev1 == SeverityLevel.CRITICAL

        sev2 = evaluate_severity(elapsed_days=15.0, target_days=5.0, overdue_days=10.0)
        assert sev2 == SeverityLevel.CRITICAL

    def test_severity_zero_target(self):
        """Target days of 0 or negative avoids ZeroDivisionError."""
        sev = evaluate_severity(elapsed_days=0.0, target_days=0.0, overdue_days=0.0)
        assert sev == SeverityLevel.OK

    def test_severity_custom_rules(self):
        """Verify custom rules configuration overrides defaults."""
        custom_rules = SeverityRulesConfig(
            warning_threshold_pct=50.0,
            breached_threshold_days=1.0,
            critical_overdue_days=5.0,
        )
        # 60% elapsed with 50% warning threshold -> WARNING
        sev = evaluate_severity(
            elapsed_days=3.0, target_days=5.0, overdue_days=0.0, rules=custom_rules
        )
        assert sev == SeverityLevel.WARNING

        # 0.5 days overdue is below custom breach threshold (1.0) -> WARNING (since 5.5/5 >= 50%)
        sev_sub_breach = evaluate_severity(
            elapsed_days=5.5, target_days=5.0, overdue_days=0.5, rules=custom_rules
        )
        assert sev_sub_breach == SeverityLevel.WARNING


# ==============================================================================
# SLA Engine Calculation Tests
# ==============================================================================

class TestSlaEngine:
    """Tests for SLA calculations, priority resolution, and summary metrics."""

    @pytest.fixture
    def engine(self):
        return SlaEngine()

    @pytest.fixture
    def fixed_now(self):
        return datetime(2024, 5, 10, 12, 0, 0, tzinfo=timezone.utc)

    # --------------------------------------------------------------------------
    # Priority Resolution
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "priority_input,expected_days",
        [
            ("P1", 1.0),
            ("p1", 1.0),
            ("Blocker", 1.0),
            ("blocker", 1.0),
            ("P2", 2.0),
            ("Critical", 2.0),
            ("P3", 5.0),
            ("Major", 5.0),
            ("P4", 10.0),
            ("Minor", 10.0),
            ("P5", 15.0),
            ("Trivial", 15.0),
            ("1 - Blocker", 1.0),
            ("P3 - Major", 5.0),
            ("Unknown Priority", 5.0),
            (None, 5.0),
            ("", 5.0),
        ],
    )
    def test_resolve_target_days(self, engine, priority_input, expected_days):
        assert engine.resolve_target_days(priority_input) == expected_days

    # --------------------------------------------------------------------------
    # Individual Record Calculation
    # --------------------------------------------------------------------------

    def test_calculate_open_ticket_compliant(self, engine, fixed_now):
        """Open ticket within SLA target window."""
        created = fixed_now - timedelta(days=2)  # 2 days elapsed
        rec = SlaRecord(
            key="APP-101",
            priority="P3",  # target: 5.0 days
            created_date=created,
            team="Backend",
        )
        processed = engine.calculate_record(rec, as_of=fixed_now)

        assert processed.sla_target_days == 5.0
        assert processed.elapsed_days == pytest.approx(2.0, abs=0.01)
        assert processed.overdue_days == 0.0
        assert processed.is_breached is False
        assert processed.severity == SeverityLevel.OK

    def test_calculate_open_ticket_warning(self, engine, fixed_now):
        """Open ticket reaching 80% of SLA target window."""
        created = fixed_now - timedelta(days=4)  # 4 days elapsed of 5 days (80%)
        rec = SlaRecord(
            key="APP-102",
            priority="P3",
            created_date=created,
            team="Backend",
        )
        processed = engine.calculate_record(rec, as_of=fixed_now)

        assert processed.elapsed_days == pytest.approx(4.0, abs=0.01)
        assert processed.overdue_days == 0.0
        assert processed.is_breached is False
        assert processed.severity == SeverityLevel.WARNING

    def test_calculate_open_ticket_breached(self, engine, fixed_now):
        """Open ticket past SLA target by 1 day."""
        created = fixed_now - timedelta(days=6)  # 6 days elapsed of 5 days (1 day overdue)
        rec = SlaRecord(
            key="APP-103",
            priority="P3",
            created_date=created,
            team="Frontend",
        )
        processed = engine.calculate_record(rec, as_of=fixed_now)

        assert processed.elapsed_days == pytest.approx(6.0, abs=0.01)
        assert processed.overdue_days == pytest.approx(1.0, abs=0.01)
        assert processed.is_breached is True
        assert processed.severity == SeverityLevel.BREACHED

    def test_calculate_open_ticket_critical(self, engine, fixed_now):
        """Open ticket past SLA target by more than 3 days."""
        created = fixed_now - timedelta(days=9)  # 9 days elapsed of 5 days (4 days overdue)
        rec = SlaRecord(
            key="APP-104",
            priority="P3",
            created_date=created,
            team="Frontend",
        )
        processed = engine.calculate_record(rec, as_of=fixed_now)

        assert processed.elapsed_days == pytest.approx(9.0, abs=0.01)
        assert processed.overdue_days == pytest.approx(4.0, abs=0.01)
        assert processed.is_breached is True
        assert processed.severity == SeverityLevel.CRITICAL

    def test_calculate_resolved_ticket(self, engine, fixed_now):
        """Resolved ticket uses resolved_date as reference instead of as_of."""
        created = fixed_now - timedelta(days=10)
        resolved = fixed_now - timedelta(days=8)  # resolved after 2 days
        rec = SlaRecord(
            key="APP-105",
            priority="P3",  # target 5 days
            created_date=created,
            resolved_date=resolved,
        )
        # Even though as_of is 10 days after created, resolved was 2 days after
        processed = engine.calculate_record(rec, as_of=fixed_now)

        assert processed.elapsed_days == pytest.approx(2.0, abs=0.01)
        assert processed.overdue_days == 0.0
        assert processed.is_breached is False
        assert processed.severity == SeverityLevel.OK

    def test_calculate_with_explicit_due_date(self, engine, fixed_now):
        """Ticket with explicit due_date calculates overdue days relative to due_date."""
        created = fixed_now - timedelta(days=5)
        due = fixed_now - timedelta(days=2)  # was due 2 days ago
        rec = SlaRecord(
            key="APP-106",
            priority="P3",
            created_date=created,
            due_date=due,
        )
        processed = engine.calculate_record(rec, as_of=fixed_now)

        assert processed.elapsed_days == pytest.approx(5.0, abs=0.01)
        assert processed.overdue_days == pytest.approx(2.0, abs=0.01)
        assert processed.is_breached is True
        assert processed.severity == SeverityLevel.BREACHED

    def test_calculate_naive_datetimes(self, engine):
        """Naive datetimes in record do not raise TypeError when compared to aware datetimes."""
        created = datetime(2024, 5, 1, 10, 0, 0)  # naive
        as_of = datetime(2024, 5, 3, 10, 0, 0, tzinfo=timezone.utc)  # aware
        rec = SlaRecord(key="APP-107", created_date=created, priority="P3")
        processed = engine.calculate_record(rec, as_of=as_of)

        assert processed.elapsed_days == pytest.approx(2.0, abs=0.01)
        assert processed.overdue_days == 0.0

    def test_calculate_missing_created_date(self, engine, fixed_now):
        """Record with missing created_date is safely initialized without error."""
        rec = SlaRecord(key="APP-108", priority="P3")
        processed = engine.calculate_record(rec, as_of=fixed_now)

        assert processed.elapsed_days == 0.0
        assert processed.overdue_days == 0.0
        assert processed.is_breached is False
        assert processed.severity == SeverityLevel.OK

    # --------------------------------------------------------------------------
    # Batch and Summary Metrics Calculation
    # --------------------------------------------------------------------------

    def test_calculate_batch(self, engine, fixed_now):
        """Batch calculation processes all records and preserves raw metadata."""
        records = [
            SlaRecord(
                key="APP-201",
                priority="P1",
                created_date=fixed_now - timedelta(days=0.5),
                raw_fields={"CustomField": "ValueA"},
            ),
            SlaRecord(
                key="APP-202",
                priority="P1",
                created_date=fixed_now - timedelta(days=5),
                raw_fields={"CustomField": "ValueB"},
            ),
        ]
        batch = engine.calculate_batch(records, as_of=fixed_now)

        assert len(batch) == 2
        assert batch[0].key == "APP-201"
        assert batch[0].severity == SeverityLevel.OK
        assert batch[0].raw_fields["CustomField"] == "ValueA"

        assert batch[1].key == "APP-202"
        assert batch[1].is_breached is True
        assert batch[1].severity == SeverityLevel.CRITICAL
        assert batch[1].raw_fields["CustomField"] == "ValueB"

    def test_calculate_summary_metrics(self, engine, fixed_now):
        """Summary metrics aggregates totals, rates, averages, and team breakdowns."""
        records = [
            # 1. OK (Backend)
            SlaRecord(
                key="REC-1",
                priority="P3",
                created_date=fixed_now - timedelta(days=1),
                team="Backend",
            ),
            # 2. Warning (Backend)
            SlaRecord(
                key="REC-2",
                priority="P3",
                created_date=fixed_now - timedelta(days=4),
                team="Backend",
            ),
            # 3. Breached (Frontend) - 1 day overdue
            SlaRecord(
                key="REC-3",
                priority="P3",
                created_date=fixed_now - timedelta(days=6),
                team="Frontend",
            ),
            # 4. Critical (Frontend) - 4 days overdue
            SlaRecord(
                key="REC-4",
                priority="P3",
                created_date=fixed_now - timedelta(days=9),
                team="Frontend",
            ),
            # 5. Breached (Unassigned) - 2 days overdue
            SlaRecord(
                key="REC-5",
                priority="P3",
                created_date=fixed_now - timedelta(days=7),
                team=None,
            ),
        ]
        calculated = engine.calculate_batch(records, as_of=fixed_now)
        metrics = engine.calculate_summary_metrics(calculated)

        assert isinstance(metrics, SlaSummaryMetrics)
        assert metrics.total_records == 5
        assert metrics.breached_count == 3
        assert metrics.warning_count == 1
        assert metrics.compliant_count == 1
        assert metrics.breach_rate_pct == pytest.approx(60.0, abs=0.1)

        # Breached overdues: 1.0, 4.0, 2.0 -> average = 7.0 / 3 = 2.33
        assert metrics.avg_overdue_days == pytest.approx(2.33, abs=0.01)
        assert metrics.max_overdue_days == pytest.approx(4.0, abs=0.01)

        # Severity counts
        assert metrics.by_severity["OK"] == 1
        assert metrics.by_severity["WARNING"] == 1
        assert metrics.by_severity["BREACHED"] == 2
        assert metrics.by_severity["CRITICAL"] == 1

        # Team counts
        assert metrics.by_team["Backend"] == {"breached": 0, "total": 2}
        assert metrics.by_team["Frontend"] == {"breached": 2, "total": 2}
        assert metrics.by_team["Unassigned"] == {"breached": 1, "total": 1}

    def test_calculate_summary_metrics_empty_records(self, engine):
        """Empty records collection produces zeroed metrics without division error."""
        metrics = engine.calculate_summary_metrics([])

        assert metrics.total_records == 0
        assert metrics.breached_count == 0
        assert metrics.warning_count == 0
        assert metrics.compliant_count == 0
        assert metrics.breach_rate_pct == 0.0
        assert metrics.avg_overdue_days == 0.0
        assert metrics.max_overdue_days == 0.0
        assert metrics.by_severity == {
            "OK": 0,
            "WARNING": 0,
            "BREACHED": 0,
            "CRITICAL": 0,
        }
        assert metrics.by_team == {}

    def test_process_extraction_result(self, engine, fixed_now):
        """ExtractionResult parsed_records are updated in-place."""
        ext_result = ExtractionResult(
            source_filename="test_table.html",
            file_type="html",
            total_rows=1,
            parsed_records=[
                SlaRecord(
                    key="TICK-1",
                    priority="P1",
                    created_date=fixed_now - timedelta(days=2),
                )
            ],
        )
        res = engine.process_extraction_result(ext_result, as_of=fixed_now)

        assert res is ext_result
        assert len(res.parsed_records) == 1
        record = res.parsed_records[0]
        assert record.is_breached is True
        assert record.overdue_days == pytest.approx(1.0, abs=0.01)
        assert record.severity == SeverityLevel.BREACHED
