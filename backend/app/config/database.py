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

    # Connection-pool tuning (ES-067, closing the ES-040 "defaults only" debt).
    # SQLAlchemy's defaults (pool 5 / overflow 10) are sized for a single
    # modest process; the request path plus two background projectors share
    # this pool, so the values are made explicit and deployment-tunable rather
    # than implicit. ``pool_recycle`` pre-empts connections dropped by an idle
    # timeout on the server or a network middlebox — ``pool_pre_ping`` (already
    # on) then has less to catch.
    pool_size: int = 5
    pool_max_overflow: int = 10
    # Seconds to wait for a free connection before failing rather than hanging.
    pool_timeout_seconds: float = 30.0
    # Seconds before a pooled connection is discarded and reopened.
    pool_recycle_seconds: int = 1800

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

    ``crypto_shred`` (ES-070, ADR-015 §6 / ADR-017 §6) selects the production
    erasure strategy: payloads are stored encrypted and erasure destroys the
    key, so bytes surviving in an immutable tier or a backup are unrecoverable.
    Off by default — the dev store deletes files, which is honest locally — and
    the key material then lives under ``<root>/keys``, a directory a deployment
    must keep **out of its backups** for shredding to mean anything.
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
    crypto_shred: bool = False


@lru_cache
def get_evidence_payload_settings() -> EvidencePayloadSettings:
    """Return the cached evidence payload store settings instance."""

    return EvidencePayloadSettings()
