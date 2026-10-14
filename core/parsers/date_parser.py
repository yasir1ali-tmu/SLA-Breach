"""Resilient multi-format date parser for SLA timestamps and ticket dates."""

from datetime import datetime, timezone
import re
from typing import Any, List, Optional, Union

from config.settings import get_sla_rules


def parse_datetime(
    value: Union[str, datetime, Any],
    formats: Optional[List[str]] = None,
    default_tz: str = "UTC",
    strict: bool = False,
) -> Optional[datetime]:
    """Parse varied date/time inputs into a timezone-aware UTC datetime.

    Handles ISO formats, custom template formats from SLA rules config,
    dirty strings (whitespace, non-breaking spaces, quotes), and textual variations.

    Args:
        value: Input string, existing datetime, or arbitrary object.
        formats: Optional list of strptime format templates. Defaults to configured rules.
        default_tz: Default timezone assumed for naive inputs (default: "UTC").
        strict: If True, raises ValueError on invalid or unparseable inputs instead of returning None.

    Returns:
        Timezone-aware UTC datetime object, or None if parsing fails and strict=False.

    Raises:
        ValueError: If strict=True and value cannot be parsed.
    """
    if value is None:
        if strict:
            raise ValueError("Cannot parse None as datetime")
        return None

    # If already a datetime, ensure timezone-aware UTC
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if not isinstance(value, str):
        if strict:
            raise ValueError(f"Expected str or datetime, received {type(value).__name__}")
        return None

    # Clean string: strip whitespace, quotes, non-breaking spaces, multiple spaces
    cleaned = value.strip().strip("'\"").replace("\xa0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        if strict:
            raise ValueError("Cannot parse empty date string")
        return None

    # Retrieve formats from config or fallback defaults
    if formats is None:
        try:
            formats = get_sla_rules().date_parsing.formats
        except Exception:
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%d/%b/%y %I:%M %p",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y",
                "%m/%d/%Y %I:%M:%S %p",
                "%m/%d/%Y %I:%M %p",
                "%m/%d/%Y",
                "%b %d, %Y %I:%M %p",
                "%d-%b-%Y",
            ]

    # Normalize a.m./p.m. variations
    norm_val = re.sub(r"(?i)\b([ap])\.m\.?", r"\1m", cleaned)

    # 1. Try configured format patterns
    for fmt in formats:
        try:
            dt = datetime.strptime(norm_val, fmt)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError):
            continue

    # 2. Fallback: ISO format parsing
    try:
        clean_iso = norm_val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_iso)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        pass

    # 3. Fallback: normalize month abbreviations / uppercase variations with configured formats
    candidate_variations = [
        norm_val.title(),
        norm_val.upper(),
        re.sub(r"(?i)\b(am|pm)\b", lambda m: m.group(1).upper(), norm_val),
    ]
    for variation in candidate_variations:
        if variation == norm_val:
            continue
        for fmt in formats:
            try:
                dt = datetime.strptime(variation, fmt)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (ValueError, TypeError):
                continue

    if strict:
        raise ValueError(f"Unable to parse date string: '{value}'")
    return None


def parse_date_safe(value: Any) -> Optional[datetime]:
    """Convenience helper to safely parse a datetime, always returning None on failure."""
    return parse_datetime(value, strict=False)
