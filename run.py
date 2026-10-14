"""Single-command application launcher for the SLA Breach Dashboard & Analyzer."""

import argparse
from typing import List, Optional
import threading
import time
import webbrowser
import uvicorn

from config.settings import get_settings


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments for the server runner.

    Args:
        args: Optional list of CLI arguments (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    settings = get_settings()

    parser = argparse.ArgumentParser(
        description=f"{settings.app_name} - Single-command Server Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=settings.host,
        help="Network interface host to bind the server to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help="Port number to bind the server to.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.debug,
        help="Enable auto-reload on code changes (default: debug setting).",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        default=False,
        help="Explicitly disable auto-reload.",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        default=False,
        help="Automatically open web browser on startup.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level.",
    )

    return parser.parse_args(args)


def resolve_reload(args: argparse.Namespace) -> bool:
    """Resolve whether auto-reload is enabled based on CLI arguments."""
    if getattr(args, "no_reload", False):
        return False
    return bool(getattr(args, "reload", False))


def print_startup_banner(host: str, port: int) -> None:
    """Print formatted ASCII banner with application details and URLs."""
    settings = get_settings()
    app_url = f"http://{host}:{port}"
    docs_url = f"http://{host}:{port}/api/docs"

    banner = f"""
======================================================================
  {settings.app_name} (v{settings.app_version})
======================================================================
  * Dashboard URL:       {app_url}
  * API Documentation:   {docs_url}
  * Host / Port:         {host}:{port}

  Status: Online and ready to accept file uploads (.html, .htm, .docx)
  Press CTRL+C to stop the server
======================================================================
"""
    print(banner)


def open_browser_delayed(url: str, delay: float = 1.0) -> threading.Thread:
    """Launch the browser in a background daemon thread after a short delay.

    Args:
        url: Destination URL to open.
        delay: Delay in seconds to allow uvicorn server to bind.

    Returns:
        The started daemon Thread instance.
    """
    def _target():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    thread = threading.Thread(target=_target, daemon=True, name="BrowserLauncher")
    thread.start()
    return thread


def main(args: Optional[List[str]] = None) -> None:
    """Main execution entry point."""
    parsed_args = parse_args(args)
    reload_flag = resolve_reload(parsed_args)
    app_url = f"http://{parsed_args.host}:{parsed_args.port}"

    if parsed_args.open_browser:
        open_browser_delayed(app_url, delay=1.0)

    print_startup_banner(parsed_args.host, parsed_args.port)

    uvicorn.run(
        "web.app:create_app",
        factory=True,
        host=parsed_args.host,
        port=parsed_args.port,
        reload=reload_flag,
        log_level=parsed_args.log_level,
    )


if __name__ == "__main__":
    main()
