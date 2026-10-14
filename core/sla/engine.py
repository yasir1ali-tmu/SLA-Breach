"""SLA calculation engine for duration, breach status, and metric aggregation."""

from datetime import datetime, timezone
import re
from typing import Dict, List, Optional

from config.settings import SlaRulesConfig, get_sla_rules
from core.models.sla import (
    ExtractionResult,
    SeverityLevel,
    SlaRecord,
    SlaSummaryMetrics,
)
from core.sla.severity import evaluate_severity


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime object is timezone-aware and converted to UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SlaEngine:
    """Core engine evaluating SLA compliance, durations, and summary metrics."""

    def __init__(self, rules: Optional[SlaRulesConfig] = None) -> None:
        """Initialize the engine with configuration rules."""
        self.rules = rules or get_sla_rules()

    def resolve_target_days(self, priority: Optional[str]) -> float:
        """Resolve SLA resolution target days from priority or fallback default.

        Performs case-insensitive matching against priority rules.

        Args:
            priority: Ticket priority label (e.g. "P1", "Blocker", "P2", "Major").

        Returns:
            Target duration in days as a float.
        """
        if not priority or not str(priority).strip():
            return float(self.rules.sla_thresholds.default_target_days)

        clean_p = str(priority).strip().lower()

        # Build normalized priority lookup map
        priority_map: Dict[str, float] = {
            k.strip().lower(): float(v)
            for k, v in self.rules.sla_thresholds.priority_targets_days.items()
        }

        # 1. Exact match (case-insensitive)
        if clean_p in priority_map:
            return priority_map[clean_p]

        # 2. Token / word boundary match (e.g. "1 - Blocker" -> matches "blocker")
        tokens = re.findall(r"\w+", clean_p)
        for token in tokens:
            if token in priority_map:
                return priority_map[token]

        return float(self.rules.sla_thresholds.default_target_days)

    def calculate_record(
        self, record: SlaRecord, as_of: Optional[datetime] = None
    ) -> SlaRecord:
        """Calculate SLA metrics, elapsed time, breach flag, and severity for a record.

        Args:
            record: SlaRecord instance to calculate.
            as_of: Reference calculation time for open tickets (defaults to current UTC time).

        Returns:
            Updated SlaRecord instance.
        """
        # Resolve target days if not already specified
        if record.sla_target_days is None or record.sla_target_days <= 0:
            record.sla_target_days = self.resolve_target_days(record.priority)
        target_days = float(record.sla_target_days)

        # Normalize reference timestamps
        as_of_time = _ensure_utc(as_of or datetime.now(timezone.utc))
        resolved_dt = _ensure_utc(record.resolved_date)
        due_dt = _ensure_utc(record.due_date)
        created_dt = _ensure_utc(record.created_date)

        # End time is resolution date if ticket is closed, else as_of
        end_time = resolved_dt if resolved_dt is not None else as_of_time

        if created_dt is not None:
            # Calculate elapsed time in days
            delta = end_time - created_dt
            elapsed_days = round(max(0.0, delta.total_seconds() / 86400.0), 2)
            record.elapsed_days = elapsed_days

            # Calculate overdue days
            if due_dt is not None:
                due_delta = end_time - due_dt
                overdue_days = round(max(0.0, due_delta.total_seconds() / 86400.0), 2)
            else:
                overdue_days = round(max(0.0, elapsed_days - target_days), 2)

            record.overdue_days = overdue_days
            record.is_breached = overdue_days > self.rules.severity_rules.breached_threshold_days
            record.severity = evaluate_severity(
                elapsed_days, target_days, overdue_days, self.rules.severity_rules
            )
        elif due_dt is not None:
            # No created date, but explicit due date present
            due_delta = end_time - due_dt
            overdue_days = round(max(0.0, due_delta.total_seconds() / 86400.0), 2)
            record.elapsed_days = 0.0
            record.overdue_days = overdue_days
            record.is_breached = overdue_days > self.rules.severity_rules.breached_threshold_days
            record.severity = evaluate_severity(
                0.0, target_days, overdue_days, self.rules.severity_rules
            )
        else:
            record.elapsed_days = 0.0
            record.overdue_days = 0.0
            record.is_breached = False
            record.severity = SeverityLevel.OK

        return record

    def calculate_batch(
        self, records: List[SlaRecord], as_of: Optional[datetime] = None
    ) -> List[SlaRecord]:
        """Apply SLA calculations to an entire list of SlaRecord items.

        Args:
            records: List of SlaRecord instances.
            as_of: Reference calculation time for open tickets.

        Returns:
            List of evaluated SlaRecord items.
        """
        return [self.calculate_record(r, as_of=as_of) for r in records]

    def calculate_summary_metrics(
        self, records: List[SlaRecord]
    ) -> SlaSummaryMetrics:
        """Aggregate summary metrics and team distributions across calculated records.

        Args:
            records: Collection of evaluated SlaRecord instances.

        Returns:
            SlaSummaryMetrics instance populated with compliance KPIs.
        """
        total_records = len(records)
        breached_count = sum(1 for r in records if r.is_breached)
        warning_count = sum(1 for r in records if r.severity == SeverityLevel.WARNING)
        compliant_count = sum(1 for r in records if r.severity == SeverityLevel.OK)

        breach_rate_pct = (
            round((breached_count / total_records) * 100.0, 1)
            if total_records > 0
            else 0.0
        )

        breached_overdues = [
            r.overdue_days
            for r in records
            if r.is_breached and r.overdue_days is not None
        ]
        avg_overdue_days = (
            round(sum(breached_overdues) / len(breached_overdues), 2)
            if breached_overdues
            else 0.0
        )

        all_overdues = [
            r.overdue_days for r in records if r.overdue_days is not None
        ]
        max_overdue_days = (
            round(max(all_overdues), 2) if all_overdues else 0.0
        )

        # Initialize severity distribution dictionary
        by_severity: Dict[str, int] = {
            SeverityLevel.OK.value: 0,
            SeverityLevel.WARNING.value: 0,
            SeverityLevel.BREACHED.value: 0,
            SeverityLevel.CRITICAL.value: 0,
        }
        for r in records:
            sev_key = (
                r.severity.value
                if isinstance(r.severity, SeverityLevel)
                else str(r.severity)
            )
            by_severity[sev_key] = by_severity.get(sev_key, 0) + 1

        # Team aggregation
        by_team: Dict[str, Dict[str, int]] = {}
        for r in records:
            team_key = (
                r.team.strip() if (r.team and r.team.strip()) else "Unassigned"
            )
            if team_key not in by_team:
                by_team[team_key] = {"breached": 0, "total": 0}
            by_team[team_key]["total"] += 1
            if r.is_breached:
                by_team[team_key]["breached"] += 1

        return SlaSummaryMetrics(
            total_records=total_records,
            breached_count=breached_count,
            warning_count=warning_count,
            compliant_count=compliant_count,
            breach_rate_pct=breach_rate_pct,
            avg_overdue_days=avg_overdue_days,
            max_overdue_days=max_overdue_days,
            by_severity=by_severity,
            by_team=by_team,
        )

    def process_extraction_result(
        self, result: ExtractionResult, as_of: Optional[datetime] = None
    ) -> ExtractionResult:
        """Process an ExtractionResult in-place by computing SLA metrics on all parsed records.

        Args:
            result: ExtractionResult from HTML or DOCX parsers.
            as_of: Reference calculation time for open tickets.

        Returns:
            Updated ExtractionResult.
        """
        result.parsed_records = self.calculate_batch(
            result.parsed_records, as_of=as_of
        )
        return result
