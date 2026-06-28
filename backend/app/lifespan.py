"""Application lifespan management.

Defines the startup and shutdown lifecycle for the FastAPI application using an
async context manager. The skeleton logs lifecycle transitions only.

This module is the designated seam for initializing and releasing long-lived
resources (for example, database connection pools). No such resources are wired
here because infrastructure integration is out of scope for the backend skeleton
(ES-002); the specifications that introduce those resources extend this lifespan.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    Code before ``yield`` runs on startup; code after ``yield`` runs on shutdown.
    """

    settings = get_settings()
    logger.info(
        "Starting %s (environment=%s)", settings.app_name, settings.app_env
    )

    yield

    logger.info("Shutting down %s", settings.app_name)
