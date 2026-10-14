"""Core SLA data models and enumerations using Pydantic v2."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class SeverityLevel(str, Enum):
    """Enumeration of SLA severity and breach status levels."""

    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    BREACHED = "BREACHED"

    @property
    def badge_class(self) -> str:
        """Return CSS classes for Tailwind UI badges."""
        mapping = {
            SeverityLevel.OK: "bg-emerald-100 text-emerald-800 border-emerald-300",
            SeverityLevel.WARNING: "bg-amber-100 text-amber-800 border-amber-300",
            SeverityLevel.CRITICAL: "bg-orange-100 text-orange-800 border-orange-300",
            SeverityLevel.BREACHED: "bg-rose-100 text-rose-800 border-rose-300",
        }
        return mapping.get(self, "bg-gray-100 text-gray-800 border-gray-300")

    @property
    def display_name(self) -> str:
        """Return human-readable display label."""
        mapping = {
            SeverityLevel.OK: "Compliant / OK",
            SeverityLevel.WARNING: "Approaching SLA",
            SeverityLevel.CRITICAL: "Critical Risk",
            SeverityLevel.BREACHED: "Breached SLA",
        }
        return mapping.get(self, self.value)


class SlaRecord(BaseModel):
    """Model representing an individual ticket SLA record."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key: str = Field(..., description="Unique ticket key or identifier (e.g., PROJ-1234)")
    summary: Optional[str] = None
    team: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    created_date: Optional[datetime] = None
    resolved_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    sla_target_days: Optional[float] = None
    elapsed_days: Optional[float] = None
    overdue_days: Optional[float] = None
    is_breached: bool = False
    severity: SeverityLevel = SeverityLevel.OK
    raw_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserves unmapped or original column values for lossless fidelity",
    )


class ExtractionResult(BaseModel):
    """Container for parsed output from table extraction modules."""

    model_config = ConfigDict(extra="ignore")

    source_filename: str
    file_type: str
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    total_rows: int = 0
    parsed_records: List[SlaRecord] = Field(default_factory=list)
    unparsed_rows: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class SlaSummaryMetrics(BaseModel):
    """Aggregated metric totals and distribution KPIs across SLA records."""

    model_config = ConfigDict(extra="ignore")

    total_records: int = 0
    breached_count: int = 0
    warning_count: int = 0
    compliant_count: int = 0
    breach_rate_pct: float = 0.0
    avg_overdue_days: float = 0.0
    max_overdue_days: float = 0.0
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_team: Dict[str, Dict[str, int]] = Field(default_factory=dict)
