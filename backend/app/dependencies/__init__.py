"""Dependency-injection providers.

This package holds **only** FastAPI dependency providers — callables intended for
use with :func:`fastapi.Depends`. It contains no business logic, services or
configuration definitions of its own; it merely exposes existing capabilities as
injectable dependencies.

The persistence providers surface the long-lived resources owned by the
persistence registry (created in the application lifespan and stored on
``app.state.persistence``) so that future services can depend on them. They add
no behaviour of their own.
"""

from collections.abc import AsyncIterator

from fastapi import Request
from neo4j import AsyncDriver
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.infrastructure.persistence.postgres.session import session_scope
from app.infrastructure.persistence.registry import PersistenceRegistry


def get_persistence(request: Request) -> PersistenceRegistry:
    """Return the persistence registry stored on the application state."""

    registry: PersistenceRegistry = request.app.state.persistence
    return registry


async def get_postgres_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a transactional async PostgreSQL session."""

    registry = get_persistence(request)
    async with session_scope(registry.session_factory) as session:
        yield session


def get_neo4j_driver(request: Request) -> AsyncDriver:
    """Return the shared Neo4j async driver."""

    return get_persistence(request).neo4j_driver


def get_qdrant_client(request: Request) -> AsyncQdrantClient:
    """Return the shared Qdrant async client."""

    return get_persistence(request).qdrant_client


def get_redis_client(request: Request) -> Redis:
    """Return the shared Redis async client."""

    return get_persistence(request).redis_client


__all__ = [
    "Settings",
    "get_settings",
    "get_persistence",
    "get_postgres_session",
    "get_neo4j_driver",
    "get_qdrant_client",
    "get_redis_client",
]
