"""Application settings.

Defines the platform/application-level configuration consumed by the backend
skeleton. Settings are loaded from environment variables (and an optional
``.env`` file) using ``pydantic-settings``.

Scope note (ES-002): only application-level configuration is modelled here.
Infrastructure connection settings (PostgreSQL, Neo4j, the Vector Database,
Redis, AI providers) are intentionally omitted because database and AI
integration are out of scope for the backend skeleton. Those settings are
introduced by the specifications that own the corresponding capabilities.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.environment import Environment, resolve_environment


class Settings(BaseSettings):
    """Application-level configuration loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SentinelAI"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    log_format: str = "text"
    # Cycle budget of the synchronous investigation run surface (ES-044,
    # slice decision V-1): small by default, configurable via RUN_CYCLE_BUDGET.
    run_cycle_budget: int = 3
    # Memory embedding outbox projector (ES-050, ADR-012): the in-process
    # background runner that drains the outbox into the vector store. Enabled by
    # default; tests disable it and drive the projector directly.
    outbox_projector_enabled: bool = True
    outbox_poll_interval_seconds: float = 2.0

    @property
    def environment(self) -> Environment:
        """The active operational environment as the typed :class:`Environment`.

        Derived from the raw ``app_env`` string; raises
        :class:`~app.config.errors.UnknownEnvironmentError` for an unrecognized
        value.
        """

        return resolve_environment(self.app_env)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance.

    The result is cached so that configuration is read from the environment
    once per process and shared across the application.
    """

    return Settings()
