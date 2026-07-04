"""AI provider configuration.

Settings for the concrete Gemini LLM adapter (ES-043, decision K-1), loaded
from the environment (and an optional ``.env`` file) with the ``GEMINI_``
prefix, mirroring the per-store pattern of :mod:`app.config.database`.

The API key is deliberately **not** a settings field: it is a protected
security asset consumed through the ``SecretProvider`` port
(``GOOGLE_API_KEY``, Secrets Management / ES-022), never a configuration
artifact.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class GeminiSettings(BaseSettings):
    """Google Gemini adapter configuration (model and execution bound)."""

    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    model: str = "gemini-3.5-flash"
    # Bounded provider execution time (ADR-013): the value is configuration,
    # the existence of the bound is the port contract.
    timeout_seconds: float = 30.0
    # Deterministic-leaning default for planning decisions.
    temperature: float = 0.0


@lru_cache
def get_gemini_settings() -> GeminiSettings:
    """Return the cached Gemini settings instance."""

    return GeminiSettings()
