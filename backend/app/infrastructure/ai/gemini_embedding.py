"""Google Gemini embedding provider adapter (ES-049, decision K-2).

Concrete realization of the provider-neutral
:class:`~app.ai.providers.embedding.EmbeddingProvider` port, over the Gemini
``embedContent`` REST API via ``httpx`` (no vendor SDK — one endpoint, one JSON
shape, explicit error mapping). Mirrors the LLM adapter
(:mod:`app.infrastructure.ai.gemini`).

Contract realization (ADR-013):

- **Bounded execution time** — every attempt runs under ``asyncio.timeout``
  with the configured bound; exceeding it raises
  :class:`~app.ai.errors.EmbeddingProviderError`, never hangs.
- **Resilience (ES-067)** — the call goes through
  :class:`~app.infrastructure.ai.resilience.ResilientHttpCaller`: bounded retry
  with backoff for transient failures behind a process-wide circuit breaker
  (ADR-013 §4). The embedding edge is the one most exposed to free-tier
  rate limits, since the projector embeds one Memory Item per record.
- **Total error mapping** — transport failures, non-success HTTP statuses
  (Gemini quota/rate-limit included), malformed payloads and empty/missing
  vectors all map to ``EmbeddingProviderError`` with a bounded, key-free
  message.
- **Key hygiene** — the API key is consumed through the ``SecretProvider``
  (``GOOGLE_API_KEY``), sent only as a request header (never the URL) and never
  logged or included in errors. A missing key surfaces as ``SecretNotFoundError``
  at construction — an explicit configuration failure.
"""

import logging

import httpx

from app.ai.errors import EmbeddingProviderError
from app.application.secrets import SecretName, SecretProvider
from app.config.ai import (
    AIResilienceSettings,
    GeminiEmbeddingSettings,
    get_ai_resilience_settings,
)
from app.infrastructure.ai.resilience import (
    ProviderCallError,
    ResilientHttpCaller,
    breaker_for,
)
from app.shared.secret import Secret

logger = logging.getLogger(__name__)

GOOGLE_API_KEY = SecretName("GOOGLE_API_KEY")

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
# Bound on provider-supplied text quoted into error messages.
_ERROR_DETAIL_LIMIT = 200
# Breaker registry key: the embedding edge has its own health signal, separate
# from the Gemini LLM edge (they are different endpoints and quotas).
PROVIDER_NAME = "gemini-embedding"


class GeminiEmbeddingProvider:
    """``EmbeddingProvider`` adapter over the Gemini ``embedContent`` API."""

    def __init__(
        self,
        settings: GeminiEmbeddingSettings,
        secrets: SecretProvider,
        transport: httpx.AsyncBaseTransport | None = None,
        resilience: AIResilienceSettings | None = None,
    ) -> None:
        self._settings = settings
        # Resolved eagerly: a missing key is a configuration error at
        # composition time (SecretNotFoundError), not a runtime failure.
        self._api_key: Secret = secrets.resolve(GOOGLE_API_KEY)
        # Injectable transport keeps the contract tests deterministic
        # (httpx.MockTransport); None means the real network.
        self._transport = transport
        policy = resilience or get_ai_resilience_settings()
        self._caller = ResilientHttpCaller(
            PROVIDER_NAME,
            settings.timeout_seconds,
            policy,
            breaker_for(PROVIDER_NAME, policy),
        )

    async def embed(self, text: str) -> tuple[float, ...]:
        """Return the embedding vector for the text within the time bound."""

        try:
            response = await self._caller.run(lambda: self._post(text))
        except ProviderCallError as exc:
            # Timeout, transport failure or an open circuit — all already
            # bounded and key-free (ES-067).
            raise EmbeddingProviderError(exc.detail) from exc

        if response.status_code != 200:
            raise EmbeddingProviderError(
                f"Gemini embedding returned HTTP {response.status_code}: "
                f"{self._error_detail(response)}"
            )
        vector = self._extract_vector(response)
        logger.info(
            "gemini embed ok model=%s dims=%s",
            self._settings.model,
            len(vector),
        )
        return vector

    async def _post(self, text: str) -> httpx.Response:
        timeout = httpx.Timeout(self._settings.timeout_seconds)
        model = self._settings.model
        async with httpx.AsyncClient(
            timeout=timeout, transport=self._transport
        ) as client:
            body: dict[str, object] = {
                "model": f"models/{model}",
                "content": {"parts": [{"text": text}]},
            }
            # A fixed output dimension keeps the vector size deterministic for
            # the Qdrant collection (ES-050); 0 or negative means "model default".
            if self._settings.dimensions > 0:
                body["outputDimensionality"] = self._settings.dimensions
            return await client.post(
                f"{_BASE_URL}/models/{model}:embedContent",
                # The key travels only as a header, never in the URL, so it
                # cannot leak through exception messages carrying the URL.
                # Stray whitespace from .env sources would be an illegal header
                # value, so the key is trimmed at use.
                headers={"x-goog-api-key": self._api_key.reveal().strip()},
                json=body,
            )

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        """A bounded, key-free detail string from a non-success response."""

        try:
            payload = response.json()
            detail = payload["error"]["message"]
        except (ValueError, KeyError, TypeError):
            detail = response.text
        if not isinstance(detail, str):
            detail = str(detail)
        return detail[:_ERROR_DETAIL_LIMIT]

    @staticmethod
    def _extract_vector(response: httpx.Response) -> tuple[float, ...]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise EmbeddingProviderError(
                "Gemini embedding returned a malformed (non-JSON) response body."
            ) from exc
        if not isinstance(payload, dict):
            raise EmbeddingProviderError(
                "Gemini embedding returned an unexpected response shape."
            )

        embedding = payload.get("embedding")
        values = embedding.get("values") if isinstance(embedding, dict) else None
        if not isinstance(values, list) or not values:
            raise EmbeddingProviderError(
                "Gemini embedding returned no vector values."
            )
        try:
            return tuple(float(v) for v in values)
        except (TypeError, ValueError) as exc:
            raise EmbeddingProviderError(
                "Gemini embedding returned non-numeric vector values."
            ) from exc
