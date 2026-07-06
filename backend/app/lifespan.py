"""Application lifespan management.

Defines the startup and shutdown lifecycle for the FastAPI application using an
async context manager.

This module is the designated seam for initializing and releasing long-lived
resources. The persistence foundation (ES-004) builds the persistence registry on
startup, stores it on ``app.state.persistence`` and closes it on shutdown. The
registry's resources are created lazily, so startup opens no network connections.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.database import get_neo4j_settings, get_postgres_settings
from app.config.settings import get_settings
from app.config.validation import validate_configuration
from app.dependencies.projector import start_outbox_projector
from app.infrastructure.persistence.registry import build_registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    Code before ``yield`` runs on startup; code after ``yield`` runs on shutdown.
    """

    settings = get_settings()
    # Configuration Validation (configuration-management §8): fail fast before
    # serving if the configuration is inconsistent with the active environment.
    environment = validate_configuration(
        settings, get_postgres_settings(), get_neo4j_settings()
    )
    logger.info(
        "Starting %s (environment=%s)", settings.app_name, environment.value
    )

    registry = build_registry()
    app.state.persistence = registry
    logger.info("Persistence registry initialized")

    # Memory embedding outbox projector (ES-050): the async, idempotent
    # background driver that derives embeddings into the vector store.
    projector_task = start_outbox_projector(registry, settings)

    try:
        yield
    finally:
        if projector_task is not None:
            projector_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await projector_task
        await registry.close()
        logger.info("Shutting down %s", settings.app_name)
