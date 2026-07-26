"""AI provider configuration.

Settings for the concrete LLM/embedding adapters — Gemini (ES-043/049,
decisions K-1/K-2), the NVIDIA NIM adapter (ES-054) — and the external
knowledge adapters (ES-058) — loaded from the environment (and an optional
``.env`` file) with per-provider prefixes, mirroring the per-store pattern of
:mod:`app.config.database`.

``LLM_PROVIDER`` selects the active LLM adapter and
``EXTERNAL_KNOWLEDGE_PROVIDERS`` the composed external knowledge adapters
(the ports stay provider-neutral, ADR-005; the selection is configuration).
API keys are deliberately **not** settings fields: they are protected security
assets consumed through the ``SecretProvider`` port (``GOOGLE_API_KEY`` /
``NVIDIA_API_KEY`` / ``NVD_API_KEY``, Secrets Management / ES-022), never
configuration artifacts.
"""

from enum import Enum
from functools import lru_cache

from pydantic import field_validator, model_validator
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

    ``LLM_FALLBACK_PROVIDER`` (ES-067) optionally names a second adapter that
    serves the call when the primary fails or its circuit is open. Unset — the
    default — keeps single-provider behavior exactly as before; naming the
    primary again is rejected (a fallback to the failing provider is no
    fallback).
    """

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    provider: LLMProviderChoice = LLMProviderChoice.GEMINI
    fallback_provider: LLMProviderChoice | None = None

    @model_validator(mode="after")
    def _distinct_fallback(self) -> "LLMSelectionSettings":
        if self.fallback_provider is self.provider:
            raise ValueError(
                "LLM_FALLBACK_PROVIDER must differ from LLM_PROVIDER."
            )
        return self


class AIResilienceSettings(BaseSettings):
    """Provider-edge resilience policy (ES-067, ADR-013 §4).

    One shared policy for every concrete AI adapter: the retry budget, its
    backoff schedule and the circuit-breaker thresholds. ADR-013 keeps these
    values out of the architecture — the *existence* of the bound is the
    contract, the numbers are configuration.

    The default attempt count is deliberately small. A retry multiplies a
    call's worst-case wall-clock time by the attempt count, and an
    investigation run makes several sequential LLM calls (the NVIDIA adapter's
    bound alone is 180s), so one retry absorbs a transient blip without
    doubling the run's latency budget. Raising it is a deployment decision.
    """

    model_config = SettingsConfigDict(
        env_prefix="AI_RESILIENCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Total attempts per call, retries included (1 disables retrying).
    max_attempts: int = 2
    backoff_base_seconds: float = 0.5
    backoff_max_seconds: float = 8.0
    # Consecutive transient failures that open a provider's circuit.
    breaker_failure_threshold: int = 5
    # How long an open circuit refuses calls before admitting one probe.
    breaker_reset_seconds: float = 30.0


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
    default execution bound is wide — 180s, the ES-059 live-demo-proven value
    (the run sequence is ~6 sequential calls; the plan's 40 rpm rate limit is
    never approached — per-call latency is the binding constraint).
    ``max_tokens`` must leave room for the model's visible reasoning plus the
    final answer.
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
    timeout_seconds: float = 180.0
    # Deterministic-leaning default for planning decisions.
    temperature: float = 0.0
    max_tokens: int = 8192


class ExternalKnowledgeProviderChoice(Enum):
    """A configured concrete external knowledge adapter (closed vocabulary)."""

    ATTACK = "attack"
    NVD = "nvd"


class ExternalKnowledgeSettings(BaseSettings):
    """Selects which external knowledge adapters the composition root builds.

    ``EXTERNAL_KNOWLEDGE_PROVIDERS=attack,nvd`` — a comma-separated closed
    vocabulary (unknown tokens are rejected at settings load). Both adapters
    are composed by default: an external-source failure is contained per
    provider by the retriever, so the live NVD integration is safe to keep on.
    An empty value opts external knowledge out entirely (the EXTERNAL
    retrieval strategy then contributes nothing, the pre-ES-058 behavior).
    """

    model_config = SettingsConfigDict(
        env_prefix="EXTERNAL_KNOWLEDGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    providers: str = "attack,nvd"

    @field_validator("providers")
    @classmethod
    def _known_providers(cls, value: str) -> str:
        for token in value.split(","):
            if token.strip():
                # Unknown tokens are rejected by the closed enum.
                ExternalKnowledgeProviderChoice(token.strip().lower())
        return value

    @property
    def selection(self) -> tuple[ExternalKnowledgeProviderChoice, ...]:
        """The configured adapters, deduplicated, in configured order."""

        selected: list[ExternalKnowledgeProviderChoice] = []
        for token in self.providers.split(","):
            if not token.strip():
                continue
            choice = ExternalKnowledgeProviderChoice(token.strip().lower())
            if choice not in selected:
                selected.append(choice)
        return tuple(selected)


class NvdSettings(BaseSettings):
    """NVD CVE external knowledge adapter configuration (ES-058).

    The NVD REST API 2.0 is a public CVE database; ``NVD_API_KEY`` is optional
    by NVD's own contract (keyless access is rate-limited harder) and is
    consumed through the ``SecretProvider``, never a field here.
    """

    model_config = SettingsConfigDict(
        env_prefix="NVD_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Bounded provider execution time (ADR-013): the value is configuration,
    # the existence of the bound is the port contract.
    timeout_seconds: float = 15.0
    # Resource bound on returned CVE items per lookup.
    results_limit: int = 5


@lru_cache
def get_llm_selection() -> LLMSelectionSettings:
    """Return the cached LLM provider selection."""

    return LLMSelectionSettings()


@lru_cache
def get_ai_resilience_settings() -> AIResilienceSettings:
    """Return the cached provider-edge resilience policy (ES-067)."""

    return AIResilienceSettings()


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


@lru_cache
def get_external_knowledge_settings() -> ExternalKnowledgeSettings:
    """Return the cached external knowledge provider selection."""

    return ExternalKnowledgeSettings()


@lru_cache
def get_nvd_settings() -> NvdSettings:
    """Return the cached NVD external knowledge settings instance."""

    return NvdSettings()
