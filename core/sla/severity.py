"""Breach severity evaluator based on configurable thresholds."""

from typing import Optional

from config.settings import SeverityRulesConfig, get_sla_rules
from core.models.sla import SeverityLevel


def evaluate_severity(
    elapsed_days: float,
    target_days: float,
    overdue_days: float,
    rules: Optional[SeverityRulesConfig] = None,
) -> SeverityLevel:
    """Evaluate SLA breach severity status for a ticket record.

    Evaluation precedence:
        1. CRITICAL: overdue_days > rules.critical_overdue_days (default > 3.0 days).
        2. BREACHED: overdue_days > rules.breached_threshold_days (default > 0.0 days).
        3. WARNING: target_days > 0 and (elapsed_days / target_days) * 100.0 >= rules.warning_threshold_pct (default >= 80%).
        4. OK: Compliant within SLA duration and below warning threshold.

    Args:
        elapsed_days: Number of days elapsed since ticket creation.
        target_days: Target SLA resolution window in days.
        overdue_days: Number of days past SLA due date / target.
        rules: Optional custom SeverityRulesConfig instance. Defaults to configured rules.

    Returns:
        SeverityLevel enum representing the ticket risk classification.
    """
    if rules is None:
        rules = get_sla_rules().severity_rules

    overdue = float(overdue_days) if overdue_days is not None else 0.0
    elapsed = float(elapsed_days) if elapsed_days is not None else 0.0
    target = float(target_days) if target_days is not None else 0.0

    # 1. Critical severity: significantly overdue past critical cutoff
    if overdue > rules.critical_overdue_days:
        return SeverityLevel.CRITICAL

    # 2. Breached severity: overdue past SLA target window
    if overdue > rules.breached_threshold_days:
        return SeverityLevel.BREACHED

    # 3. Warning severity: approaching SLA target (e.g. >= 80% elapsed)
    if target > 0:
        elapsed_pct = (elapsed / target) * 100.0
        if elapsed_pct >= rules.warning_threshold_pct:
            return SeverityLevel.WARNING

    # 4. Compliant
    return SeverityLevel.OK
