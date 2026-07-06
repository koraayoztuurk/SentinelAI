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
    """Google Gemini LLM adapter configuration (model and execution bound)."""

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


class GeminiEmbeddingSettings(BaseSettings):
    """Google Gemini embedding adapter configuration (ES-049, decision K-2).

    Separate from :class:`GeminiSettings` so the embedding model and its
    execution bound evolve independently of the LLM model. The API key is not a
    field here either — it is consumed through the ``SecretProvider``
    (``GOOGLE_API_KEY``), shared with the LLM adapter.
    """

    model_config = SettingsConfigDict(
        env_prefix="GEMINI_EMBEDDING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # The concrete embedding model id is an implementation choice (adjustable
    # via GEMINI_EMBEDDING_MODEL); the provider decision (Gemini) is K-2.
    model: str = "gemini-embedding-001"
    # Bounded provider execution time (ADR-013).
    timeout_seconds: float = 30.0
    # Fixed output dimension (requested via the API's ``outputDimensionality``)
    # so the Qdrant collection's vector size is deterministic (ES-050).
    dimensions: int = 768


@lru_cache
def get_gemini_settings() -> GeminiSettings:
    """Return the cached Gemini LLM settings instance."""

    return GeminiSettings()


@lru_cache
def get_gemini_embedding_settings() -> GeminiEmbeddingSettings:
    """Return the cached Gemini embedding settings instance."""

    return GeminiEmbeddingSettings()
