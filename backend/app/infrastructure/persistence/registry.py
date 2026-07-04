"""Persistence resource registry.

Internal infrastructure detail that owns the lifecycle of the long-lived
persistence resources: the PostgreSQL engine and session factory, and the Neo4j,
Qdrant and Redis clients. It is created on application startup and closed on
shutdown.

This is not a service locator or a general dependency container. It exposes only
named, typed fields and a single :meth:`close` method; it has no ``get(key)`` or
``register(key)`` API. Its sole responsibility is lifecycle ownership.
"""

from dataclasses import dataclass

from neo4j import AsyncDriver
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config.database import (
    get_neo4j_settings,
    get_postgres_settings,
    get_qdrant_settings,
    get_redis_settings,
)
from app.infrastructure.persistence.neo4j.driver import create_driver
from app.infrastructure.persistence.postgres.engine import (
    create_engine,
    create_session_factory,
)
from app.infrastructure.persistence.qdrant.client import (
    create_client as create_qdrant_client,
)
from app.infrastructure.persistence.redis.client import (
    create_client as create_redis_client,
)


@dataclass(slots=True)
class PersistenceRegistry:
    """Holds the long-lived persistence resources for the application's lifetime."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    neo4j_driver: AsyncDriver
    qdrant_client: AsyncQdrantClient
    redis_client: Redis

    async def close(self) -> None:
        """Release every persistence resource."""

        await self.engine.dispose()
        await self.neo4j_driver.close()
        await self.qdrant_client.close()
        await self.redis_client.aclose()

    async def ping_postgres(self) -> None:
        """Perform a trivial PostgreSQL round trip (readiness probing).

        Raises whatever the driver raises when the store is unreachable; the
        caller decides how to report it.
        """

        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))


def build_registry() -> PersistenceRegistry:
    """Create the persistence registry.

    Resources are created lazily and no network connections are opened here, so
    this is safe to call during application startup without live databases.
    """

    engine = create_engine(get_postgres_settings())
    return PersistenceRegistry(
        engine=engine,
        session_factory=create_session_factory(engine),
        neo4j_driver=create_driver(get_neo4j_settings()),
        qdrant_client=create_qdrant_client(get_qdrant_settings()),
        redis_client=create_redis_client(get_redis_settings()),
    )
