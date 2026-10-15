"""Application configuration models, loaders, and column resolver."""

from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union
import yaml

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationConfig(BaseModel):
    """Application metadata and general upload limits."""

    model_config = ConfigDict(extra="ignore")

    name: str = "SLA Breach Dashboard & Analyzer"
    version: str = "1.0.0"
    debug: bool = False
    max_upload_size_mb: int = 25
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [".html", ".htm", ".docx"]
    )


class SlaThresholdsConfig(BaseModel):
    """SLA target durations in days."""

    model_config = ConfigDict(extra="ignore")

    default_target_days: float = 5.0
    priority_targets_days: Dict[str, float] = Field(default_factory=dict)


class SeverityRulesConfig(BaseModel):
    """Thresholds determining warning, critical, and breach statuses."""

    model_config = ConfigDict(extra="ignore")

    warning_threshold_pct: float = 80.0
    breached_threshold_days: float = 0.0
    critical_overdue_days: float = 3.0


class ColumnMappingsConfig(BaseModel):
    """Alias mappings for resolving inconsistent table headers to canonical fields."""

    model_config = ConfigDict(extra="ignore")

    ticket_id: List[str] = Field(default_factory=list)
    summary: List[str] = Field(default_factory=list)
    status: List[str] = Field(default_factory=list)
    priority: List[str] = Field(default_factory=list)
    created_date: List[str] = Field(default_factory=list)
    resolved_date: List[str] = Field(default_factory=list)
    due_date: List[str] = Field(default_factory=list)
    team: List[str] = Field(default_factory=list)


class DateParsingConfig(BaseModel):
    """Datetime parsing configurations and format strings."""

    model_config = ConfigDict(extra="ignore")

    default_timezone: str = "UTC"
    formats: List[str] = Field(default_factory=list)


class SlaRulesConfig(BaseModel):
    """Composite configuration model for SLA calculation and table ingestion."""

    model_config = ConfigDict(extra="ignore")

    application: Optional[ApplicationConfig] = None
    sla_thresholds: SlaThresholdsConfig = Field(default_factory=SlaThresholdsConfig)
    severity_rules: SeverityRulesConfig = Field(default_factory=SeverityRulesConfig)
    column_mappings: ColumnMappingsConfig = Field(default_factory=ColumnMappingsConfig)
    date_parsing: DateParsingConfig = Field(default_factory=DateParsingConfig)


class AppSettings(BaseSettings):
    """Environment-driven global application settings."""

    app_name: str = "SLA Breach Dashboard & Analyzer"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    max_upload_size_mb: int = 25
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [".html", ".htm", ".docx"]
    )
    rules_config_path: Path = Path("config/default_sla_rules.yaml")

    model_config = SettingsConfigDict(
        env_prefix="SLA_",
        env_file=".env",
        extra="ignore",
    )


def load_sla_rules(config_path: Optional[Union[Path, str]] = None) -> SlaRulesConfig:
    """Load and validate SLA rules configuration from a YAML file.

    Args:
        config_path: Optional file path. If None, uses settings.rules_config_path.

    Returns:
        Validated SlaRulesConfig instance.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the file is not valid YAML or fails Pydantic schema validation.
    """
    if config_path is None:
        target_path = get_settings().rules_config_path
        if not target_path.is_file():
            alt_path = Path(__file__).resolve().parent / "default_sla_rules.yaml"
            if alt_path.is_file():
                target_path = alt_path
    else:
        target_path = Path(config_path)

    if not target_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {target_path}")


    try:
        with open(target_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except Exception as exc:
        raise ValueError(
            f"Failed to parse YAML configuration from {target_path}: {exc}"
        ) from exc

    if not isinstance(raw_data, dict):
        raise ValueError(
            f"Configuration file {target_path} must contain a YAML dictionary mapping"
        )

    try:
        return SlaRulesConfig(**raw_data)
    except ValidationError as exc:
        raise ValueError(
            f"Invalid SLA configuration schema in {target_path}: {exc}"
        ) from exc


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached AppSettings singleton."""
    return AppSettings()


@lru_cache(maxsize=1)
def get_sla_rules() -> SlaRulesConfig:
    """Return cached default SlaRulesConfig singleton."""
    return load_sla_rules()


def clear_config_caches() -> None:
    """Clear cached settings and rules singletons for testing or configuration reload."""
    get_settings.cache_clear()
    get_sla_rules.cache_clear()


def normalize_header(header: str) -> str:
    """Normalize column header for case- and punctuation-insensitive matching."""
    if not header:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", header.lower())
    cleaned = re.sub(r"[\s_]+", " ", cleaned)
    return cleaned.strip()


def resolve_column_name(
    header: str, mappings: ColumnMappingsConfig
) -> Optional[str]:
    """Resolve an incoming table header to a canonical schema field name.

    Normalizes input header (lowercase, strip whitespace, remove punctuation)
    and checks against canonical field names and alias lists.

    Args:
        header: Raw table column header from HTML/DOCX table.
        mappings: ColumnMappingsConfig containing canonical field aliases.

    Returns:
        Canonical field name (e.g. 'ticket_id', 'created_date') if matched,
        or None if no match is found.
    """
    if not header or not isinstance(header, str):
        return None

    norm_target = normalize_header(header)
    if not norm_target:
        return None

    mapping_dict = mappings.model_dump()
    for field_name, aliases in mapping_dict.items():
        # Check canonical field name directly
        if norm_target == normalize_header(field_name):
            return field_name

        # Check aliases
        if isinstance(aliases, list):
            for alias in aliases:
                if norm_target == normalize_header(alias):
                    return field_name

    return None
