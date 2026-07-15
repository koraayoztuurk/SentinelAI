"""Contract tests for the NVIDIA NIM LLM provider adapter (ES-054).

Deterministic, network-free validation over ``httpx.MockTransport``: the
adapter realizes the ``LLMProvider`` port contract — bounded execution time,
total error mapping to ``LLMProviderError`` (quota, choice-less, malformed
payloads, transport failures), strict key hygiene (Authorization header only,
never part of an error message) and reasoning-block normalization
(``<think>…</think>`` stripped from the answer). Plain test functions.
"""

import asyncio
import json
import os

import httpx
import pytest

from app.ai.errors import LLMProviderError
from app.ai.providers.llm import LLMRequest
from app.application.secrets import SecretName, SecretNotFoundError
from app.config.ai import NvidiaSettings
from app.infrastructure.ai.nvidia import NvidiaLLMProvider
from app.infrastructure.secrets import EnvironmentSecretProvider
from app.shared.secret import Secret

_API_KEY = "nvapi-test-9c1d"


class _FixedSecrets:
    """SecretProvider double returning one fixed key."""

    def resolve(self, name: SecretName) -> Secret:
        assert name == SecretName("NVIDIA_API_KEY")
        return Secret(_API_KEY)


def _settings(timeout_seconds: float = 5.0) -> NvidiaSettings:
    return NvidiaSettings(
        model="test/model-x",
        timeout_seconds=timeout_seconds,
        temperature=0.0,
        max_tokens=1024,
    )


def _provider(
    transport: httpx.MockTransport, timeout_seconds: float = 5.0
) -> NvidiaLLMProvider:
    return NvidiaLLMProvider(
        _settings(timeout_seconds), _FixedSecrets(), transport=transport
    )


def _success_body(content: str) -> dict[str, object]:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


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
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"
    # Key hygiene: never in the URL.
    assert _API_KEY not in str(request.url)
    assert str(request.url).endswith("/v1/chat/completions")
    body = json.loads(request.content)
    assert body["model"] == "test/model-x"
    assert body["messages"] == [{"role": "user", "content": "decide"}]
    assert body["temperature"] == 0.0
    assert body["max_tokens"] == 1024
    assert body["stream"] is False


def test_reasoning_think_block_is_stripped_from_the_answer() -> None:
    content = (
        "<think>the user asks for a decision; evidence suggests"
        " completing.</think>\n"
        '{"action":"control","control":"complete"}'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_success_body(content))

    provider = _provider(httpx.MockTransport(handler))
    response = asyncio.run(provider.generate(LLMRequest(prompt="p")))

    assert response.text == '{"action":"control","control":"complete"}'


def test_reasoning_only_content_maps_to_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=_success_body("<think>hmm, unsure…</think>")
        )

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(LLMProviderError, match="reasoning only"):
        asyncio.run(provider.generate(LLMRequest(prompt="p")))


# -------------------------------------------------------------- error mapping


def test_rate_limit_maps_to_provider_error_without_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, json={"error": {"message": "rate limit exceeded"}}
        )

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(LLMProviderError) as excinfo:
        asyncio.run(provider.generate(LLMRequest(prompt="p")))
    assert "429" in str(excinfo.value)
    assert _API_KEY not in str(excinfo.value)


def test_server_error_maps_to_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(LLMProviderError, match="503"):
        asyncio.run(provider.generate(LLMRequest(prompt="p")))


def test_choiceless_response_maps_to_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(LLMProviderError, match="no choices"):
        asyncio.run(provider.generate(LLMRequest(prompt="p")))


def test_missing_content_maps_to_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant"}}]}
        )

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(LLMProviderError, match="no message content"):
        asyncio.run(provider.generate(LLMRequest(prompt="p")))


def test_malformed_body_maps_to_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(LLMProviderError, match="malformed"):
        asyncio.run(provider.generate(LLMRequest(prompt="p")))


def test_transport_failure_maps_to_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(LLMProviderError, match="transport failure"):
        asyncio.run(provider.generate(LLMRequest(prompt="p")))


def test_slow_provider_hits_the_execution_bound() -> None:
    async def slow_handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1.0)
        return httpx.Response(200, json=_success_body("late"))

    provider = _provider(httpx.MockTransport(slow_handler), timeout_seconds=0.05)
    with pytest.raises(LLMProviderError, match="execution bound"):
        asyncio.run(provider.generate(LLMRequest(prompt="p")))


# ---------------------------------------------------------------- key hygiene


def test_missing_key_is_a_configuration_error_at_construction() -> None:
    os.environ.pop("NVIDIA_API_KEY", None)
    with pytest.raises(SecretNotFoundError):
        NvidiaLLMProvider(_settings(), EnvironmentSecretProvider())
