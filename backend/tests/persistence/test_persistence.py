"""Unit tests for the persistence foundation (ES-004).

Plain pytest functions only — no fixtures, no live databases.
"""

import asyncio

from pydantic import SecretStr

from app.config.database import (
    Neo4jSettings,
    PostgresSettings,
    QdrantSettings,
    RedisSettings,
)
from app.domain.repositories import Repository
from app.infrastructure.persistence.registry import (
    PersistenceRegistry,
    build_registry,
)


def test_postgres_dsn_is_async_and_well_formed() -> None:
    settings = PostgresSettings(
        host="db", port=6000, user="u", password=SecretStr("p"), db="mydb"
    )
    assert settings.dsn == "postgresql+asyncpg://u:p@db:6000/mydb"


def test_postgres_password_is_not_exposed_in_repr() -> None:
    settings = PostgresSettings(password=SecretStr("supersecret"))
    assert "supersecret" not in repr(settings)
    assert isinstance(settings.password, SecretStr)


def test_redis_url_is_built_from_host_and_port() -> None:
    assert RedisSettings(host="cache", port=6380).url == "redis://cache:6380"


def test_default_store_urls_match_env_example() -> None:
    assert QdrantSettings().url == "http://qdrant:6333"
    assert Neo4jSettings().uri == "bolt://neo4j:7687"


def test_repository_port_is_a_protocol_with_no_operations() -> None:
    assert getattr(Repository, "_is_protocol", False) is True
    # A pure marker: it declares no persistence operations.
    operations = {name for name in vars(Repository) if not name.startswith("_")}
    assert operations == set()


def test_build_registry_creates_resources_without_connecting() -> None:
    registry = build_registry()
    assert isinstance(registry, PersistenceRegistry)
    assert registry.engine is not None
    assert registry.session_factory is not None
    assert registry.neo4j_driver is not None
    assert registry.qdrant_client is not None
    assert registry.redis_client is not None


def test_registry_close_releases_resources() -> None:
    registry = build_registry()
    asyncio.run(registry.close())
