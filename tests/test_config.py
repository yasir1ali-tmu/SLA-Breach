"""Unit tests for configuration loading, AppSettings, and column resolution."""

from pathlib import Path
import pytest

from config.settings import (
    AppSettings,
    ColumnMappingsConfig,
    SeverityRulesConfig,
    SlaRulesConfig,
    SlaThresholdsConfig,
    clear_config_caches,
    get_settings,
    get_sla_rules,
    load_sla_rules,
    resolve_column_name,
)


@pytest.fixture(autouse=True)
def reset_caches():
    """Ensure cached singletons are reset before and after each test."""
    clear_config_caches()
    yield
    clear_config_caches()


def test_load_default_sla_rules():
    """Verify loading default SLA rules configuration from YAML file."""
    config = load_sla_rules()
    assert isinstance(config, SlaRulesConfig)
    assert config.application is not None
    assert config.application.name == "SLA Breach Dashboard & Analyzer"

    # Threshold checks
    assert config.sla_thresholds.default_target_days == 5.0
    assert config.sla_thresholds.priority_targets_days["P1"] == 1.0
    assert config.sla_thresholds.priority_targets_days["P2"] == 2.0
    assert config.sla_thresholds.priority_targets_days["P3"] == 5.0
    assert config.sla_thresholds.priority_targets_days["Blocker"] == 1.0

    # Severity rules
    assert config.severity_rules.warning_threshold_pct == 80.0
    assert config.severity_rules.breached_threshold_days == 0.0
    assert config.severity_rules.critical_overdue_days == 3.0

    # Column mappings
    assert "Key" in config.column_mappings.ticket_id
    assert "Issue key" in config.column_mappings.ticket_id
    assert "Assignee" in config.column_mappings.team

    # Date parsing
    assert config.date_parsing.default_timezone == "UTC"
    assert len(config.date_parsing.formats) > 0


def test_cached_get_sla_rules():
    """Verify get_sla_rules returns cached singleton."""
    rules1 = get_sla_rules()
    rules2 = get_sla_rules()
    assert rules1 is rules2


def test_resolve_column_name_variants():
    """Verify column alias resolution across casing, delimiters, and synonyms."""
    rules = load_sla_rules()
    mappings = rules.column_mappings

    # Ticket ID synonyms
    assert resolve_column_name("Issue Key", mappings) == "ticket_id"
    assert resolve_column_name("issue_key", mappings) == "ticket_id"
    assert resolve_column_name("Key", mappings) == "ticket_id"
    assert resolve_column_name("Ticket ID", mappings) == "ticket_id"
    assert resolve_column_name("ID", mappings) == "ticket_id"
    assert resolve_column_name("Incident ID", mappings) == "ticket_id"
    assert resolve_column_name("ticket_id", mappings) == "ticket_id"

    # Created date synonyms
    assert resolve_column_name("Created Date", mappings) == "created_date"
    assert resolve_column_name("Date Created", mappings) == "created_date"
    assert resolve_column_name("Open Date", mappings) == "created_date"
    assert resolve_column_name("Created", mappings) == "created_date"
    assert resolve_column_name("created_date", mappings) == "created_date"

    # Resolved date synonyms
    assert resolve_column_name("Resolved", mappings) == "resolved_date"
    assert resolve_column_name("Resolution Date", mappings) == "resolved_date"
    assert resolve_column_name("Closed Date", mappings) == "resolved_date"

    # Summary synonyms
    assert resolve_column_name("Summary", mappings) == "summary"
    assert resolve_column_name("Title", mappings) == "summary"
    assert resolve_column_name("Issue summary", mappings) == "summary"
    assert resolve_column_name("Description", mappings) == "summary"

    # Team synonyms
    assert resolve_column_name("Assignee", mappings) == "team"
    assert resolve_column_name("Assigned Team", mappings) == "team"
    assert resolve_column_name("Owner", mappings) == "team"
    assert resolve_column_name("Department", mappings) == "team"

    # Priority & Status
    assert resolve_column_name("Priority", mappings) == "priority"
    assert resolve_column_name("Severity", mappings) == "priority"
    assert resolve_column_name("Status", mappings) == "status"
    assert resolve_column_name("Issue Status", mappings) == "status"

    # Due date
    assert resolve_column_name("Due Date", mappings) == "due_date"
    assert resolve_column_name("Target Date", mappings) == "due_date"
    assert resolve_column_name("Deadline", mappings) == "due_date"


def test_resolve_column_name_unmapped_and_invalid():
    """Verify resolve_column_name returns None for unknown or invalid inputs."""
    mappings = ColumnMappingsConfig(ticket_id=["Key", "Ticket ID"])

    assert resolve_column_name("NonExistentHeader123", mappings) is None
    assert resolve_column_name("", mappings) is None
    assert resolve_column_name("   ", mappings) is None
    assert resolve_column_name(None, mappings) is None  # type: ignore[arg-type]


def test_app_settings_defaults():
    """Verify default values in AppSettings."""
    settings = AppSettings()
    assert settings.app_name == "SLA Breach Dashboard & Analyzer"
    assert settings.app_version == "1.0.0"
    assert settings.debug is False
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.max_upload_size_mb == 25
    assert ".html" in settings.allowed_extensions
    assert ".docx" in settings.allowed_extensions


def test_app_settings_environment_override(monkeypatch):
    """Verify environment variables with SLA_ prefix override default settings."""
    monkeypatch.setenv("SLA_DEBUG", "true")
    monkeypatch.setenv("SLA_PORT", "9000")
    monkeypatch.setenv("SLA_HOST", "0.0.0.0")

    settings = AppSettings()
    assert settings.debug is True
    assert settings.port == 9000
    assert settings.host == "0.0.0.0"


def test_load_sla_rules_nonexistent_file(tmp_path):
    """Verify FileNotFoundError is raised when target config file does not exist."""
    missing_file = tmp_path / "missing_rules.yaml"
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        load_sla_rules(missing_file)


def test_load_sla_rules_corrupted_yaml(tmp_path):
    """Verify ValueError is raised when parsing malformed YAML syntax."""
    corrupted_file = tmp_path / "corrupted.yaml"
    corrupted_file.write_text("sla_thresholds: [unclosed list", encoding="utf-8")

    with pytest.raises(ValueError, match="Failed to parse YAML configuration"):
        load_sla_rules(corrupted_file)


def test_load_sla_rules_non_dict_yaml(tmp_path):
    """Verify ValueError is raised when YAML root is not a mapping."""
    list_file = tmp_path / "list_root.yaml"
    list_file.write_text("- item 1\n- item 2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a YAML dictionary mapping"):
        load_sla_rules(list_file)


def test_load_sla_rules_invalid_schema(tmp_path):
    """Verify ValueError is raised when configuration values violate schema types."""
    invalid_schema_file = tmp_path / "invalid_schema.yaml"
    invalid_schema_file.write_text(
        "sla_thresholds:\n  default_target_days: 'not-a-number'\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid SLA configuration schema"):
        load_sla_rules(invalid_schema_file)
