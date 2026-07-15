"""AI provider configuration.

Settings for the concrete LLM/embedding adapters — Gemini (ES-043/049,
decisions K-1/K-2) and the NVIDIA NIM adapter (ES-054) — loaded from the
environment (and an optional ``.env`` file) with per-provider prefixes,
mirroring the per-store pattern of :mod:`app.config.database`.

``LLM_PROVIDER`` selects the active LLM adapter (the port stays
provider-neutral, ADR-005; the selection is configuration). API keys are
deliberately **not** settings fields: they are protected security assets
consumed through the ``SecretProvider`` port (``GOOGLE_API_KEY`` /
``NVIDIA_API_KEY``, Secrets Management / ES-022), never configuration
artifacts.
"""

from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderChoice(Enum):
    """The configured concrete LLM adapter (closed vocabulary)."""

    GEMINI = "gemini"
    NVIDIA = "nvidia"


class LLMSelectionSettings(BaseSettings):
    """Selects which concrete LLM adapter the composition root builds.

    ``LLM_PROVIDER=gemini|nvidia`` — an unknown value is rejected by the
    closed enum. Embedding stays on the Gemini adapter regardless (the
    Qdrant collection's vector dimension is bound to it, ES-050).
    """

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    provider: LLMProviderChoice = LLMProviderChoice.GEMINI


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


class NvidiaSettings(BaseSettings):
    """NVIDIA NIM LLM adapter configuration (ES-054).

    The NIM API is OpenAI-compatible (``/v1/chat/completions``); the concrete
    model id is configuration (``NVIDIA_MODEL``, default MiniMax-M3 — owner
    decision). Reasoning models answer slower than flash-class models, so the
    default execution bound is wider; ``max_tokens`` must leave room for the
    model's visible reasoning plus the final answer.
    """

    model_config = SettingsConfigDict(
        env_prefix="NVIDIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    model: str = "minimaxai/minimax-m3"
    # Bounded provider execution time (ADR-013): the value is configuration,
    # the existence of the bound is the port contract.
    timeout_seconds: float = 90.0
    # Deterministic-leaning default for planning decisions.
    temperature: float = 0.0
    max_tokens: int = 8192


@lru_cache
def get_llm_selection() -> LLMSelectionSettings:
    """Return the cached LLM provider selection."""

    return LLMSelectionSettings()


@lru_cache
def get_nvidia_settings() -> NvidiaSettings:
    """Return the cached NVIDIA NIM LLM settings instance."""

    return NvidiaSettings()


@lru_cache
def get_gemini_settings() -> GeminiSettings:
    """Return the cached Gemini LLM settings instance."""

    return GeminiSettings()


@lru_cache
def get_gemini_embedding_settings() -> GeminiEmbeddingSettings:
    """Return the cached Gemini embedding settings instance."""

    return GeminiEmbeddingSettings()
