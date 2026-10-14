"""Analytics aggregation engine for SLA breach reporting and Chart.js dashboards."""

from typing import Any, Dict, List
from core.models.sla import SeverityLevel, SlaRecord


def compute_overdue_distribution(records: List[SlaRecord]) -> Dict[str, int]:
    """Group overdue tickets into 4 discrete histogram bins.

    Bins:
        - "0-1d": 0.0 < overdue_days <= 1.0
        - "1-3d": 1.0 < overdue_days <= 3.0
        - "3-7d": 3.0 < overdue_days <= 7.0
        - ">7d": overdue_days > 7.0

    Tickets with overdue_days <= 0 or None are ignored.

    Args:
        records: Collection of evaluated SlaRecord instances.

    Returns:
        Dictionary mapping bin labels to count of overdue tickets.
    """
    bins: Dict[str, int] = {
        "0-1d": 0,
        "1-3d": 0,
        "3-7d": 0,
        ">7d": 0,
    }

    for record in records:
        days = record.overdue_days
        if days is None or days <= 0.0:
            continue

        if days <= 1.0:
            bins["0-1d"] += 1
        elif days <= 3.0:
            bins["1-3d"] += 1
        elif days <= 7.0:
            bins["3-7d"] += 1
        else:
            bins[">7d"] += 1

    return bins


def compute_severity_distribution(records: List[SlaRecord]) -> Dict[str, int]:
    """Count occurrences of each SeverityLevel across all records.

    Ensures all 4 severity levels (OK, WARNING, CRITICAL, BREACHED) are present
    with non-negative counts.

    Args:
        records: Collection of evaluated SlaRecord instances.

    Returns:
        Dictionary mapping severity level names to ticket counts.
    """
    counts: Dict[str, int] = {
        SeverityLevel.OK.value: 0,
        SeverityLevel.WARNING.value: 0,
        SeverityLevel.CRITICAL.value: 0,
        SeverityLevel.BREACHED.value: 0,
    }

    for record in records:
        sev = record.severity
        sev_key = sev.value if isinstance(sev, SeverityLevel) else str(sev)
        if sev_key in counts:
            counts[sev_key] += 1
        else:
            counts[sev_key] = counts.get(sev_key, 0) + 1

    return counts


def compute_team_rankings(records: List[SlaRecord]) -> List[Dict[str, Any]]:
    """Aggregate ticket counts, breach counts, and compliance rates per team.

    Treats empty, None, or whitespace-only team names as 'Unassigned'.
    Ranks teams by breached count descending, then breach_rate_pct descending,
    then team name ascending.

    Args:
        records: Collection of evaluated SlaRecord instances.

    Returns:
        Sorted list of team metrics dictionaries.
    """
    team_data: Dict[str, Dict[str, Any]] = {}

    for record in records:
        team_name = record.team
        if team_name is None or not str(team_name).strip():
            team_key = "Unassigned"
        else:
            team_key = str(team_name).strip()

        if team_key not in team_data:
            team_data[team_key] = {
                "team": team_key,
                "total": 0,
                "breached": 0,
            }

        team_data[team_key]["total"] += 1
        if record.is_breached:
            team_data[team_key]["breached"] += 1

    rankings: List[Dict[str, Any]] = []
    for team_key, stats in team_data.items():
        total = stats["total"]
        breached = stats["breached"]
        compliant = total - breached
        breach_rate = round((breached / total) * 100.0, 1) if total > 0 else 0.0

        rankings.append(
            {
                "team": team_key,
                "total": total,
                "breached": breached,
                "compliant": compliant,
                "breach_rate_pct": breach_rate,
            }
        )

    # Sort: breached descending, breach_rate_pct descending, team name ascending
    rankings.sort(key=lambda t: (-t["breached"], -t["breach_rate_pct"], t["team"]))
    return rankings


def compute_analytics_payload(records: List[SlaRecord]) -> Dict[str, Any]:
    """Consolidate overdue histogram, severity breakdown, and team breach rankings.

    Args:
        records: Collection of evaluated SlaRecord instances.

    Returns:
        Structured dictionary containing overdue_distribution, severity_distribution,
        team_rankings, and summary KPIs.
    """
    total_records = len(records)
    breached_records = [r for r in records if r.is_breached]
    breached_count = len(breached_records)
    breach_rate_pct = (
        round((breached_count / total_records) * 100.0, 1)
        if total_records > 0
        else 0.0
    )

    breached_overdues = [
        r.overdue_days
        for r in breached_records
        if r.overdue_days is not None
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

    return {
        "overdue_distribution": compute_overdue_distribution(records),
        "severity_distribution": compute_severity_distribution(records),
        "team_rankings": compute_team_rankings(records),
        "summary": {
            "total_records": total_records,
            "breached_count": breached_count,
            "breach_rate_pct": breach_rate_pct,
            "avg_overdue_days": avg_overdue_days,
            "max_overdue_days": max_overdue_days,
        },
    }
