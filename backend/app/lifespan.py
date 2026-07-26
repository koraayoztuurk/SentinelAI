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

from app.application.audit import AuditAction
from app.config.ai import get_llm_selection
from app.config.auth import get_auth_selection
from app.config.database import get_neo4j_settings, get_postgres_settings
from app.config.settings import get_settings
from app.config.validation import validate_configuration
from app.dependencies.audit import build_audit_recorder, record_lifecycle_event
from app.dependencies.projector import (
    start_erasure_projector,
    start_outbox_projector,
)
from app.dependencies.retention import start_retention_sweeper
from app.infrastructure.persistence.registry import build_registry
from app.infrastructure.secrets import EnvironmentSecretProvider

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    Code before ``yield`` runs on startup; code after ``yield`` runs on shutdown.
    """

    settings = get_settings()
    # Configuration Validation (configuration-management §8): fail fast before
    # serving if the configuration is inconsistent with the active environment.
    # ES-069 extends it to secret *availability*: outside development, a
    # deployment that cannot perform its configured capabilities does not enter
    # service (secrets-management §6). The provider is supplied here because
    # the composition root owns the secret store.
    environment = validate_configuration(
        settings,
        get_postgres_settings(),
        get_neo4j_settings(),
        auth=get_auth_selection(),
        llm=get_llm_selection(),
        secrets=EnvironmentSecretProvider(),
    )
    logger.info(
        "Starting %s (environment=%s)", settings.app_name, environment.value
    )

    registry = build_registry()
    app.state.persistence = registry
    logger.info("Persistence registry initialized")

    # Durable audit sink (ES-069, ADR-018): bound here rather than in the
    # application factory because it needs the session factory the registry
    # owns. Until this point the log-only recorder is in place, so audit is
    # never unbound.
    app.state.audit_recorder = build_audit_recorder(registry)
    await record_lifecycle_event(app, AuditAction.SERVICE_STARTED)

    # Memory embedding outbox projector (ES-050): the async, idempotent
    # background driver that derives embeddings into the vector store.
    projector_task = start_outbox_projector(registry, settings)
    # Evidence payload erasure projector (ES-065, ADR-017 §5): drains the
    # erasure intent carried by investigation tombstones into the object store.
    erasure_task = start_erasure_projector(registry, settings)
    # Retention sweep (ES-070, data-lifecycle §3): enforces the configured
    # retention duration through the same erase path an analyst uses. Starts
    # only when a duration is configured — a destructive automation must be
    # asked for, never defaulted into.
    retention_task = start_retention_sweeper(registry, settings)

    try:
        yield
    finally:
        # Recorded before the stores close, while the sink can still accept it.
        await record_lifecycle_event(app, AuditAction.SERVICE_STOPPED)
        for task in (projector_task, erasure_task, retention_task):
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        await registry.close()
        logger.info("Shutting down %s", settings.app_name)
