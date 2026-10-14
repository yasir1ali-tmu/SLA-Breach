"""FastAPI application factory and lifecycle configuration."""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.settings import AppSettings, get_settings
from web.api.routes import router as api_router

logger = logging.getLogger(__name__)


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI ASGI application.

    Args:
        settings: Optional AppSettings instance. Uses cached singleton if None.

    Returns:
        Configured FastAPI instance with middleware, router, and exception handlers.
    """
    app_settings = settings or get_settings()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.debug,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS configuration for browser clients and local dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "status_code": exc.status_code},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled application error on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)},
        )

    # Template and static assets configuration
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    # Mount static files directory
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Root route serving dashboard UI
    @app.get("/", summary="Dashboard web user interface")
    async def index(request: Request):
        """Render the main multi-tab SLA breach dashboard interface."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "request": request,
                "app_name": app_settings.app_name,
                "version": app_settings.app_version,
            },
        )

    # Include REST API endpoints under /api prefix
    app.include_router(api_router, prefix="/api")

    return app


# Expose default ASGI app instance for uvicorn runner
app = create_app()
