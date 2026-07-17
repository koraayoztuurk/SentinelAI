"""Persistence configuration.

Per-store connection settings for the persistence foundation, loaded from the
environment (and an optional ``.env`` file) using ``pydantic-settings``. Each
store has its own settings class and ``env_prefix`` mirroring ``.env.example``.

Credentials are held as ``SecretStr`` so their values are not exposed through
logging or representation, consistent with the Secrets Management architecture
(least exposure; secrets never logged).

These classes define configuration only. Creating connections is the
responsibility of the infrastructure persistence modules.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    """PostgreSQL connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = "postgres"
    port: int = 5432
    db: str = "sentinelai"
    user: str = "sentinelai"
    password: SecretStr = SecretStr("change_me")

    @property
    def dsn(self) -> str:
        """Return the async SQLAlchemy DSN for this PostgreSQL configuration."""

        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class Neo4jSettings(BaseSettings):
    """Neo4j connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    uri: str = "bolt://neo4j:7687"
    user: str = "neo4j"
    password: SecretStr = SecretStr("change_me")


class QdrantSettings(BaseSettings):
    """Qdrant (vector database) connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="QDRANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    url: str = "http://qdrant:6333"


class RedisSettings(BaseSettings):
    """Redis connection settings.

    Provides a connection primitive only; this layer defines no cache keys,
    semantics or usage. Caching behaviour is owned by the services that require it.
    """

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = "redis"
    port: int = 6379

    @property
    def url(self) -> str:
        """Return the Redis connection URL for this configuration."""

        return f"redis://{self.host}:{self.port}"


@lru_cache
def get_postgres_settings() -> PostgresSettings:
    """Return the cached PostgreSQL settings instance."""

    return PostgresSettings()


@lru_cache
def get_neo4j_settings() -> Neo4jSettings:
    """Return the cached Neo4j settings instance."""

    return Neo4jSettings()


@lru_cache
def get_qdrant_settings() -> QdrantSettings:
    """Return the cached Qdrant settings instance."""

    return QdrantSettings()


@lru_cache
def get_redis_settings() -> RedisSettings:
    """Return the cached Redis settings instance."""

    return RedisSettings()


class EvidencePayloadSettings(BaseSettings):
    """Evidence payload store settings (ES-060, ADR-015 §4).

    ``root`` is the content-addressed filesystem store's base directory
    (relative paths resolve against the process working directory — the dev
    default; deployments set an absolute path onto a mounted volume).
    ``max_bytes`` bounds a single uploaded payload at the API boundary.
    """

    model_config = SettingsConfigDict(
        env_prefix="EVIDENCE_PAYLOAD_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    root: str = "var/evidence-payloads"
    max_bytes: int = 10 * 1024 * 1024


@lru_cache
def get_evidence_payload_settings() -> EvidencePayloadSettings:
    """Return the cached evidence payload store settings instance."""

    return EvidencePayloadSettings()
