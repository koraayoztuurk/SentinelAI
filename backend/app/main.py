"""Application entry point.

Builds and configures the FastAPI application via an application factory. The
factory wires together the cross-cutting infrastructure of the backend skeleton:
centralized logging, lifecycle management, exception handling and routing.

The module-level ``app`` instance is the ASGI application served by, for example,
``uvicorn app.main:app``.
"""

from fastapi import FastAPI

from app import __version__
from app.application.audit import LoggingAuditRecorder
from app.config.settings import get_settings
from app.core.logging import configure_logging
from app.lifespan import lifespan
from app.presentation.api.audit import AuditMiddleware
from app.presentation.api.context import RequestContextMiddleware
from app.presentation.api.v1 import api_v1_router
from app.presentation.exception_handlers import register_exception_handlers
from app.presentation.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.state.audit_recorder = LoggingAuditRecorder()

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(AuditMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
