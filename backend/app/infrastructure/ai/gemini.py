"""Google Gemini LLM provider adapter (ES-043, decision K-1).

First concrete realization of the provider-neutral
:class:`~app.ai.providers.llm.LLMProvider` port, over the Gemini
``generateContent`` REST API via ``httpx`` (no vendor SDK — one endpoint, one
JSON shape, explicit error mapping).

Contract realization (ADR-013):

- **Bounded execution time** — every call runs under ``asyncio.timeout`` with
  the configured bound (httpx gets the same value as its network timeout);
  exceeding it raises :class:`~app.ai.errors.LLMProviderError`, never hangs.
- **Total error mapping** — network/transport failures, non-success HTTP
  statuses (including Gemini quota/rate-limit responses), safety-blocked or
  candidate-less responses and malformed payloads all map to
  ``LLMProviderError`` with a bounded, key-free message.
- **Key hygiene** — the API key is consumed through the ``SecretProvider``
  port (``GOOGLE_API_KEY``, ES-022's first real consumer), sent only as a
  request header (never in the URL) and never included in errors or logs. A
  missing key surfaces as ``SecretNotFoundError`` at construction — an
  explicit configuration failure, distinct from runtime provider failures.
"""

import asyncio
import logging

import httpx

from app.ai.errors import LLMProviderError
from app.ai.providers.llm import LLMRequest, LLMResponse
from app.application.secrets import SecretName, SecretProvider
from app.config.ai import GeminiSettings
from app.shared.secret import Secret

logger = logging.getLogger(__name__)

GOOGLE_API_KEY = SecretName("GOOGLE_API_KEY")

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
# Bound on provider-supplied text quoted into error messages.
_ERROR_DETAIL_LIMIT = 200


class GeminiLLMProvider:
    """``LLMProvider`` adapter over the Gemini ``generateContent`` API."""

    def __init__(
        self,
        settings: GeminiSettings,
        secrets: SecretProvider,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        # Resolved eagerly: a missing key is a configuration error at
        # composition time (SecretNotFoundError), not a runtime LLM failure.
        self._api_key: Secret = secrets.resolve(GOOGLE_API_KEY)
        # Injectable transport keeps the contract tests deterministic
        # (httpx.MockTransport); None means the real network.
        self._transport = transport

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate text for the request within the configured time bound."""

        try:
            async with asyncio.timeout(self._settings.timeout_seconds):
                response = await self._post(request)
        except TimeoutError as exc:
            raise LLMProviderError(
                f"Gemini call exceeded the {self._settings.timeout_seconds}s "
                f"execution bound."
            ) from exc
        except httpx.HTTPError as exc:
            # Transport-level failure (connect/read/write, DNS, TLS...).
            raise LLMProviderError(
                f"Gemini transport failure: {type(exc).__name__}."
            ) from exc

        if response.status_code != 200:
            raise LLMProviderError(
                f"Gemini returned HTTP {response.status_code}: "
                f"{self._error_detail(response)}"
            )
        text = self._extract_text(response)
        logger.info(
            "gemini generate ok model=%s chars=%s",
            self._settings.model,
            len(text),
        )
        return LLMResponse(text=text)

    async def _post(self, request: LLMRequest) -> httpx.Response:
        timeout = httpx.Timeout(self._settings.timeout_seconds)
        async with httpx.AsyncClient(
            timeout=timeout, transport=self._transport
        ) as client:
            return await client.post(
                f"{_BASE_URL}/models/{self._settings.model}:generateContent",
                # The key travels only as a header, never in the URL, so it
                # can never leak through exception messages carrying the URL.
                # Stray whitespace from .env/env_file sources would be an
                # illegal header value, so the key is trimmed at use.
                headers={"x-goog-api-key": self._api_key.reveal().strip()},
                json={
                    "contents": [{"parts": [{"text": request.prompt}]}],
                    "generationConfig": {
                        "temperature": self._settings.temperature
                    },
                },
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
    def _extract_text(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError as exc:
            raise LLMProviderError(
                "Gemini returned a malformed (non-JSON) response body."
            ) from exc
        if not isinstance(payload, dict):
            raise LLMProviderError("Gemini returned an unexpected response shape.")

        feedback = payload.get("promptFeedback")
        if isinstance(feedback, dict) and feedback.get("blockReason"):
            raise LLMProviderError(
                f"Gemini blocked the prompt: {feedback['blockReason']}."
            )

        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise LLMProviderError("Gemini returned no candidates.")
        first = candidates[0]
        if not isinstance(first, dict):
            raise LLMProviderError("Gemini returned an unexpected candidate shape.")
        finish_reason = first.get("finishReason")
        if finish_reason == "SAFETY":
            raise LLMProviderError("Gemini blocked the response (safety).")

        content = first.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            raise LLMProviderError("Gemini returned no content parts.")
        texts = [
            part["text"]
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        if not texts:
            raise LLMProviderError("Gemini returned no text content.")
        return "".join(texts)
