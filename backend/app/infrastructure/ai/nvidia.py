"""NVIDIA NIM LLM provider adapter (ES-054).

Second concrete realization of the provider-neutral
:class:`~app.ai.providers.llm.LLMProvider` port, over the NVIDIA NIM
OpenAI-compatible ``/v1/chat/completions`` REST API via ``httpx`` (no vendor
SDK — one endpoint, one JSON shape, explicit error mapping). The default
model is MiniMax-M3 (owner decision; ``NVIDIA_MODEL`` is configuration).

Contract realization (ADR-013), mirroring the Gemini adapter (ES-043):

- **Bounded execution time** — every call runs under ``asyncio.timeout`` with
  the configured bound (httpx gets the same value as its network timeout).
- **Total error mapping** — transport failures, non-success HTTP statuses
  (quota/rate-limit included), choice-less or malformed payloads all map to
  ``LLMProviderError`` with a bounded, key-free message.
- **Key hygiene** — the API key is consumed through the ``SecretProvider``
  port (``NVIDIA_API_KEY``), sent only as the ``Authorization`` header and
  never included in errors or logs; missing key surfaces as
  ``SecretNotFoundError`` at construction.

Reasoning normalization: M-class models may emit their visible reasoning as a
``<think>…</think>`` block inside ``message.content`` (or in a separate
``reasoning_content`` field, which this adapter ignores). The port's
``LLMResponse.text`` is the **answer**, so think blocks are stripped — the
consuming agents (strict-JSON transformations) must never have to parse
provider-specific reasoning artifacts.
"""

import asyncio
import logging
import re

import httpx

from app.ai.errors import LLMProviderError
from app.ai.providers.llm import LLMRequest, LLMResponse
from app.application.secrets import SecretName, SecretProvider
from app.config.ai import NvidiaSettings
from app.shared.secret import Secret

logger = logging.getLogger(__name__)

NVIDIA_API_KEY = SecretName("NVIDIA_API_KEY")

_BASE_URL = "https://integrate.api.nvidia.com/v1"
# Bound on provider-supplied text quoted into error messages.
_ERROR_DETAIL_LIMIT = 200
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


class NvidiaLLMProvider:
    """``LLMProvider`` adapter over the NVIDIA NIM chat-completions API."""

    def __init__(
        self,
        settings: NvidiaSettings,
        secrets: SecretProvider,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        # Resolved eagerly: a missing key is a configuration error at
        # composition time (SecretNotFoundError), not a runtime LLM failure.
        self._api_key: Secret = secrets.resolve(NVIDIA_API_KEY)
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
                f"NVIDIA call exceeded the {self._settings.timeout_seconds}s "
                f"execution bound."
            ) from exc
        except httpx.HTTPError as exc:
            # Transport-level failure (connect/read/write, DNS, TLS...).
            raise LLMProviderError(
                f"NVIDIA transport failure: {type(exc).__name__}."
            ) from exc

        if response.status_code != 200:
            raise LLMProviderError(
                f"NVIDIA returned HTTP {response.status_code}: "
                f"{self._error_detail(response)}"
            )
        text = self._extract_text(response)
        logger.info(
            "nvidia generate ok model=%s chars=%s",
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
                f"{_BASE_URL}/chat/completions",
                # The key travels only as a header, never in the URL, so it
                # can never leak through exception messages carrying the URL.
                # Stray whitespace from .env sources would be an illegal
                # header value, so the key is trimmed at use.
                headers={
                    "Authorization": (
                        f"Bearer {self._api_key.reveal().strip()}"
                    ),
                    "Accept": "application/json",
                },
                json={
                    "model": self._settings.model,
                    "messages": [
                        {"role": "user", "content": request.prompt}
                    ],
                    "max_tokens": self._settings.max_tokens,
                    "temperature": self._settings.temperature,
                    "stream": False,
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
                "NVIDIA returned a malformed (non-JSON) response body."
            ) from exc
        if not isinstance(payload, dict):
            raise LLMProviderError(
                "NVIDIA returned an unexpected response shape."
            )

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMProviderError("NVIDIA returned no choices.")
        first = choices[0]
        if not isinstance(first, dict):
            raise LLMProviderError(
                "NVIDIA returned an unexpected choice shape."
            )
        message = first.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise LLMProviderError("NVIDIA returned no message content.")

        # Normalize away the visible reasoning block; the port contract is
        # the answer text (see module docstring).
        text = _THINK_BLOCK.sub("", content).strip()
        if not text:
            raise LLMProviderError(
                "NVIDIA returned no answer content (reasoning only)."
            )
        return text
