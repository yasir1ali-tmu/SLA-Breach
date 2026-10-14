"""Unit tests for SLA analytics engine and metric aggregations."""

from datetime import datetime, timezone
import pytest

from core.analytics.metrics import (
    compute_analytics_payload,
    compute_overdue_distribution,
    compute_severity_distribution,
    compute_team_rankings,
)
from core.models.sla import SeverityLevel, SlaRecord


def test_empty_records_analytics() -> None:
    """Verify empty record list returns zeroed distributions, empty rankings, and safe summary."""
    records = []

    overdue = compute_overdue_distribution(records)
    assert overdue == {"0-1d": 0, "1-3d": 0, "3-7d": 0, ">7d": 0}

    severity = compute_severity_distribution(records)
    assert severity == {"OK": 0, "WARNING": 0, "CRITICAL": 0, "BREACHED": 0}

    teams = compute_team_rankings(records)
    assert teams == []

    payload = compute_analytics_payload(records)
    assert payload["overdue_distribution"] == overdue
    assert payload["severity_distribution"] == severity
    assert payload["team_rankings"] == []
    assert payload["summary"] == {
        "total_records": 0,
        "breached_count": 0,
        "breach_rate_pct": 0.0,
        "avg_overdue_days": 0.0,
        "max_overdue_days": 0.0,
    }


def test_overdue_distribution_bins() -> None:
    """Verify boundary conditions and binning for overdue durations."""
    records = [
        # Should be excluded (<= 0 or None)
        SlaRecord(key="T-1", overdue_days=None),
        SlaRecord(key="T-2", overdue_days=-2.5),
        SlaRecord(key="T-3", overdue_days=0.0),
        # 0-1d bin: 0 < days <= 1.0
        SlaRecord(key="T-4", overdue_days=0.1),
        SlaRecord(key="T-5", overdue_days=1.0),
        # 1-3d bin: 1.0 < days <= 3.0
        SlaRecord(key="T-6", overdue_days=1.01),
        SlaRecord(key="T-7", overdue_days=2.5),
        SlaRecord(key="T-8", overdue_days=3.0),
        # 3-7d bin: 3.0 < days <= 7.0
        SlaRecord(key="T-9", overdue_days=3.1),
        SlaRecord(key="T-10", overdue_days=7.0),
        # >7d bin: days > 7.0
        SlaRecord(key="T-11", overdue_days=7.01),
        SlaRecord(key="T-12", overdue_days=15.4),
    ]

    bins = compute_overdue_distribution(records)
    assert bins["0-1d"] == 2
    assert bins["1-3d"] == 3
    assert bins["3-7d"] == 2
    assert bins[">7d"] == 2


def test_severity_distribution() -> None:
    """Verify exact count per severity level across mixed tickets."""
    records = [
        SlaRecord(key="T-1", severity=SeverityLevel.OK),
        SlaRecord(key="T-2", severity=SeverityLevel.OK),
        SlaRecord(key="T-3", severity=SeverityLevel.WARNING),
        SlaRecord(key="T-4", severity=SeverityLevel.CRITICAL),
        SlaRecord(key="T-5", severity=SeverityLevel.CRITICAL),
        SlaRecord(key="T-6", severity=SeverityLevel.CRITICAL),
        SlaRecord(key="T-7", severity=SeverityLevel.BREACHED),
    ]

    dist = compute_severity_distribution(records)
    assert dist["OK"] == 2
    assert dist["WARNING"] == 1
    assert dist["CRITICAL"] == 3
    assert dist["BREACHED"] == 1


def test_team_rankings_aggregation_and_sorting() -> None:
    """Verify team metric aggregation and primary/secondary sorting logic."""
    records = [
        # Alpha: 3 total, 2 breached -> 66.7%
        SlaRecord(key="T-1", team="Alpha", is_breached=True),
        SlaRecord(key="T-2", team="Alpha", is_breached=True),
        SlaRecord(key="T-3", team="Alpha", is_breached=False),
        # Beta: 2 total, 2 breached -> 100.0%
        SlaRecord(key="T-4", team="Beta", is_breached=True),
        SlaRecord(key="T-5", team="Beta", is_breached=True),
        # Gamma: 5 total, 1 breached -> 20.0%
        SlaRecord(key="T-6", team="Gamma", is_breached=True),
        SlaRecord(key="T-7", team="Gamma", is_breached=False),
        SlaRecord(key="T-8", team="Gamma", is_breached=False),
        SlaRecord(key="T-9", team="Gamma", is_breached=False),
        SlaRecord(key="T-10", team="Gamma", is_breached=False),
        # Delta: 4 total, 0 breached -> 0.0%
        SlaRecord(key="T-11", team="Delta", is_breached=False),
        SlaRecord(key="T-12", team="Delta", is_breached=False),
        SlaRecord(key="T-13", team="Delta", is_breached=False),
        SlaRecord(key="T-14", team="Delta", is_breached=False),
    ]

    rankings = compute_team_rankings(records)
    assert len(rankings) == 4

    # Both Beta and Alpha have breached=2. Beta has 100% breach_rate, Alpha has 66.7%.
    # Beta should be first.
    assert rankings[0]["team"] == "Beta"
    assert rankings[0]["total"] == 2
    assert rankings[0]["breached"] == 2
    assert rankings[0]["compliant"] == 0
    assert rankings[0]["breach_rate_pct"] == 100.0

    assert rankings[1]["team"] == "Alpha"
    assert rankings[1]["total"] == 3
    assert rankings[1]["breached"] == 2
    assert rankings[1]["compliant"] == 1
    assert rankings[1]["breach_rate_pct"] == 66.7

    assert rankings[2]["team"] == "Gamma"
    assert rankings[2]["total"] == 5
    assert rankings[2]["breached"] == 1
    assert rankings[2]["compliant"] == 4
    assert rankings[2]["breach_rate_pct"] == 20.0

    assert rankings[3]["team"] == "Delta"
    assert rankings[3]["total"] == 4
    assert rankings[3]["breached"] == 0
    assert rankings[3]["compliant"] == 4
    assert rankings[3]["breach_rate_pct"] == 0.0


def test_unassigned_team_fallback() -> None:
    """Verify missing, None, and whitespace team values normalize to 'Unassigned'."""
    records = [
        SlaRecord(key="T-1", team=None, is_breached=True),
        SlaRecord(key="T-2", team="", is_breached=False),
        SlaRecord(key="T-3", team="   ", is_breached=True),
        SlaRecord(key="T-4", team="Platform", is_breached=False),
    ]

    rankings = compute_team_rankings(records)
    unassigned = next((t for t in rankings if t["team"] == "Unassigned"), None)
    assert unassigned is not None
    assert unassigned["total"] == 3
    assert unassigned["breached"] == 2
    assert unassigned["compliant"] == 1
    assert unassigned["breach_rate_pct"] == 66.7


def test_full_analytics_payload() -> None:
    """Verify consolidated analytics payload structure, types, and summary metrics."""
    records = [
        SlaRecord(key="T-1", team="DevOps", is_breached=True, overdue_days=4.5, severity=SeverityLevel.BREACHED),
        SlaRecord(key="T-2", team="DevOps", is_breached=True, overdue_days=10.0, severity=SeverityLevel.BREACHED),
        SlaRecord(key="T-3", team="QA", is_breached=False, overdue_days=-1.0, severity=SeverityLevel.OK),
    ]

    payload = compute_analytics_payload(records)

    assert "overdue_distribution" in payload
    assert payload["overdue_distribution"]["3-7d"] == 1
    assert payload["overdue_distribution"][">7d"] == 1

    assert "severity_distribution" in payload
    assert payload["severity_distribution"]["BREACHED"] == 2
    assert payload["severity_distribution"]["OK"] == 1

    assert "team_rankings" in payload
    assert len(payload["team_rankings"]) == 2
    assert payload["team_rankings"][0]["team"] == "DevOps"

    summary = payload["summary"]
    assert summary["total_records"] == 3
    assert summary["breached_count"] == 2
    assert summary["breach_rate_pct"] == 66.7
    assert summary["avg_overdue_days"] == 7.25  # (4.5 + 10.0) / 2
    assert summary["max_overdue_days"] == 10.0
