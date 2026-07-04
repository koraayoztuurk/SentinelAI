"""Contract tests for the Gemini LLM provider adapter (ES-043).

Deterministic, network-free validation over ``httpx.MockTransport``: the
adapter realizes the ``LLMProvider`` port contract — bounded execution time,
total error mapping to ``LLMProviderError`` (quota, safety block, malformed
payloads, transport failures) and strict key hygiene (header-only transport,
never part of an error message). Plain test functions, no fixtures.
"""

import asyncio
import json
import os

import httpx
import pytest

from app.ai.errors import LLMProviderError
from app.ai.providers.llm import LLMRequest
from app.application.secrets import SecretName, SecretNotFoundError
from app.config.ai import GeminiSettings
from app.infrastructure.ai.gemini import GeminiLLMProvider
from app.infrastructure.secrets import EnvironmentSecretProvider
from app.shared.secret import Secret

_API_KEY = "test-key-6f2a"


class _FixedSecrets:
    """SecretProvider double returning one fixed key."""

    def resolve(self, name: SecretName) -> Secret:
        assert name == SecretName("GOOGLE_API_KEY")
        return Secret(_API_KEY)


def _settings(timeout_seconds: float = 5.0) -> GeminiSettings:
    return GeminiSettings(
        model="gemini-test", timeout_seconds=timeout_seconds, temperature=0.0
    )


def _provider(
    handler: httpx.MockTransport, timeout_seconds: float = 5.0
) -> GeminiLLMProvider:
    return GeminiLLMProvider(
        _settings(timeout_seconds), _FixedSecrets(), transport=handler
    )


def _success_body(text: str) -> dict[str, object]:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


# ----------------------------------------------------------------- happy path


def test_generate_returns_text_and_sends_key_only_as_header() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_success_body('{"action":"control"}'))

    provider = _provider(httpx.MockTransport(handler))
    response = asyncio.run(provider.generate(LLMRequest(prompt="decide")))

    assert response.text == '{"action":"control"}'
    request = captured[0]
    assert request.headers["x-goog-api-key"] == _API_KEY
    # Key hygiene: never in the URL; model and endpoint are in the path.
    assert _API_KEY not in str(request.url)
    assert "models/gemini-test:generateContent" in str(request.url)
    body = json.loads(request.content)
    assert body["contents"][0]["parts"][0]["text"] == "decide"
    assert body["generationConfig"]["temperature"] == 0.0


def test_multiple_parts_are_joined() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": "a"}, {"text": "b"}]}}
                ]
            },
        )

    provider = _provider(httpx.MockTransport(handler))
    assert asyncio.run(provider.generate(LLMRequest(prompt="p"))).text == "ab"


# -------------------------------------------------------------- error mapping


def _assert_llm_error(provider: GeminiLLMProvider, *needles: str) -> None:
    with pytest.raises(LLMProviderError) as excinfo:
        asyncio.run(provider.generate(LLMRequest(prompt="p")))
    message = str(excinfo.value)
    for needle in needles:
        assert needle in message
    # Key hygiene: no failure mode may reveal the key.
    assert _API_KEY not in message
    assert excinfo.value.code == "ai.llm_provider_error"


def test_quota_and_rate_limit_map_to_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, json={"error": {"message": "Resource has been exhausted"}}
        )

    _assert_llm_error(
        _provider(httpx.MockTransport(handler)), "429", "exhausted"
    )


def test_server_error_maps_to_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal")

    _assert_llm_error(_provider(httpx.MockTransport(handler)), "500")


def test_prompt_block_maps_to_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"promptFeedback": {"blockReason": "SAFETY"}, "candidates": []},
        )

    _assert_llm_error(_provider(httpx.MockTransport(handler)), "SAFETY")


def test_safety_finish_reason_maps_to_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"candidates": [{"finishReason": "SAFETY"}]}
        )

    _assert_llm_error(_provider(httpx.MockTransport(handler)), "safety")


def test_no_candidates_maps_to_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    _assert_llm_error(_provider(httpx.MockTransport(handler)), "no candidates")


def test_malformed_body_maps_to_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json at all")

    _assert_llm_error(_provider(httpx.MockTransport(handler)), "malformed")


def test_transport_failure_maps_to_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    _assert_llm_error(
        _provider(httpx.MockTransport(handler)), "transport", "ConnectError"
    )


def test_execution_bound_is_enforced_and_never_hangs() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(10)
        return httpx.Response(200, json=_success_body("late"))

    provider = _provider(httpx.MockTransport(handler), timeout_seconds=0.05)
    _assert_llm_error(provider, "execution bound")


# ---------------------------------------------------------------- key hygiene


def test_missing_key_is_an_explicit_configuration_error() -> None:
    saved = os.environ.pop("GOOGLE_API_KEY", None)
    try:
        with pytest.raises(SecretNotFoundError) as excinfo:
            GeminiLLMProvider(_settings(), EnvironmentSecretProvider())
        assert excinfo.value.code == "secret.not_found"
        assert "GOOGLE_API_KEY" in str(excinfo.value)
    finally:
        if saved is not None:
            os.environ["GOOGLE_API_KEY"] = saved
