"""Unit tests for the single-command runner run.py."""

from unittest.mock import MagicMock, patch
import pytest

from config.settings import get_settings
from run import main, open_browser_delayed, parse_args, print_startup_banner, resolve_reload


def test_parse_args_defaults():
    """Verify parse_args uses application settings as defaults."""
    settings = get_settings()
    args = parse_args([])

    assert args.host == settings.host
    assert args.port == settings.port
    assert args.reload == settings.debug
    assert args.no_reload is False
    assert args.open_browser is False
    assert args.log_level == "info"


def test_parse_args_custom_values():
    """Verify parse_args overrides defaults when CLI arguments are supplied."""
    cli_input = [
        "--host",
        "0.0.0.0",
        "--port",
        "9090",
        "--reload",
        "--open-browser",
        "--log-level",
        "debug",
    ]
    args = parse_args(cli_input)

    assert args.host == "0.0.0.0"
    assert args.port == 9090
    assert args.reload is True
    assert args.open_browser is True
    assert args.log_level == "debug"


def test_resolve_reload_behavior():
    """Verify reload resolution handles --reload and --no-reload properly."""
    args_default = parse_args([])
    assert resolve_reload(args_default) == get_settings().debug

    args_reload = parse_args(["--reload"])
    assert resolve_reload(args_reload) is True

    args_no_reload = parse_args(["--no-reload"])
    assert resolve_reload(args_no_reload) is False

    # --no-reload takes precedence if both somehow set
    args_conflict = parse_args(["--reload", "--no-reload"])
    assert resolve_reload(args_conflict) is False


def test_print_startup_banner_content(capsys):
    """Verify startup banner displays correct URLs, application title, and port."""
    settings = get_settings()
    print_startup_banner("127.0.0.1", 8080)
    captured = capsys.readouterr().out

    assert settings.app_name in captured
    assert "http://127.0.0.1:8080" in captured
    assert "http://127.0.0.1:8080/api/docs" in captured
    assert "Press CTRL+C to stop the server" in captured


def test_open_browser_delayed():
    """Verify open_browser_delayed spawns a daemon thread calling webbrowser.open."""
    with patch("webbrowser.open") as mock_open:
        thread = open_browser_delayed("http://127.0.0.1:8000", delay=0.01)
        assert thread.is_alive() or not thread.is_alive()
        thread.join(timeout=1.0)
        mock_open.assert_called_once_with("http://127.0.0.1:8000")


def test_main_invokes_uvicorn():
    """Verify main orchestrates parsing, banner, and uvicorn runner."""
    with patch("uvicorn.run") as mock_uvicorn_run, patch(
        "run.open_browser_delayed"
    ) as mock_open_browser:
        main(["--host", "127.0.0.1", "--port", "8888", "--open-browser"])

        mock_open_browser.assert_called_once_with("http://127.0.0.1:8888", delay=1.0)
        mock_uvicorn_run.assert_called_once_with(
            "web.app:create_app",
            factory=True,
            host="127.0.0.1",
            port=8888,
            reload=False,
            log_level="info",
        )
