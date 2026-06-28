"""Application entry point.

Builds and configures the FastAPI application via an application factory. The
factory wires together the cross-cutting infrastructure of the backend skeleton:
centralized logging, lifecycle management, exception handling and routing.

The module-level ``app`` instance is the ASGI application served by, for example,
``uvicorn app.main:app``.
"""

from fastapi import FastAPI

from app import __version__
from app.config.settings import get_settings
from app.core.logging import configure_logging
from app.lifespan import lifespan
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

    register_exception_handlers(app)
    app.include_router(health_router)

    return app


app = create_app()
