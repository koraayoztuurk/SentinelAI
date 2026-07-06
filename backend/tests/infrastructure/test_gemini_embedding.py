"""Contract tests for the Gemini embedding adapter (ES-049).

Deterministic, network-free validation over ``httpx.MockTransport`` (mirrors
``test_gemini_provider.py``): the adapter realizes the ``EmbeddingProvider``
port contract — bounded execution time, total error mapping to
``EmbeddingProviderError`` (quota, malformed, empty vector, transport failures)
and strict key hygiene (header-only transport, never in an error message).
Plain test functions, no fixtures.
"""

import asyncio
import json
import os

import httpx
import pytest

from app.ai.errors import EmbeddingProviderError
from app.application.secrets import SecretName, SecretNotFoundError
from app.config.ai import GeminiEmbeddingSettings
from app.infrastructure.ai.gemini_embedding import GeminiEmbeddingProvider
from app.infrastructure.secrets import EnvironmentSecretProvider
from app.shared.secret import Secret

_API_KEY = "test-key-7c3d"


class _FixedSecrets:
    """SecretProvider double returning one fixed key."""

    def resolve(self, name: SecretName) -> Secret:
        assert name == SecretName("GOOGLE_API_KEY")
        return Secret(_API_KEY)


def _settings(timeout_seconds: float = 5.0) -> GeminiEmbeddingSettings:
    return GeminiEmbeddingSettings(
        model="embed-test", timeout_seconds=timeout_seconds
    )


def _provider(
    handler: httpx.MockTransport, timeout_seconds: float = 5.0
) -> GeminiEmbeddingProvider:
    return GeminiEmbeddingProvider(
        _settings(timeout_seconds), _FixedSecrets(), transport=handler
    )


def _vector_body(values: list[float]) -> dict[str, object]:
    return {"embedding": {"values": values}}


# ----------------------------------------------------------------- happy path


def test_embed_returns_vector_and_sends_key_only_as_header() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_vector_body([0.1, 0.2, 0.3]))

    provider = _provider(httpx.MockTransport(handler))
    vector = asyncio.run(provider.embed("beacon to rare domain"))

    assert vector == (0.1, 0.2, 0.3)
    request = captured[0]
    assert request.headers["x-goog-api-key"] == _API_KEY
    # Key hygiene: never in the URL; model + endpoint are in the path.
    assert _API_KEY not in str(request.url)
    assert "models/embed-test:embedContent" in str(request.url)
    body = json.loads(request.content)
    assert body["content"]["parts"][0]["text"] == "beacon to rare domain"
    assert body["model"] == "models/embed-test"


# -------------------------------------------------------------- error mapping


def _assert_embedding_error(
    provider: GeminiEmbeddingProvider, *needles: str
) -> None:
    with pytest.raises(EmbeddingProviderError) as excinfo:
        asyncio.run(provider.embed("x"))
    message = str(excinfo.value)
    for needle in needles:
        assert needle in message
    assert _API_KEY not in message
    assert excinfo.value.code == "ai.embedding_provider_error"


def test_quota_and_rate_limit_map_to_embedding_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, json={"error": {"message": "Resource has been exhausted"}}
        )

    _assert_embedding_error(
        _provider(httpx.MockTransport(handler)), "429", "exhausted"
    )


def test_server_error_maps_to_embedding_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal")

    _assert_embedding_error(_provider(httpx.MockTransport(handler)), "500")


def test_empty_vector_maps_to_embedding_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_vector_body([]))

    _assert_embedding_error(_provider(httpx.MockTransport(handler)), "no vector")


def test_missing_embedding_field_maps_to_embedding_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    _assert_embedding_error(_provider(httpx.MockTransport(handler)), "no vector")


def test_non_numeric_values_map_to_embedding_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_vector_body(["not", "numeric"]))  # type: ignore[list-item]

    _assert_embedding_error(_provider(httpx.MockTransport(handler)), "non-numeric")


def test_malformed_body_maps_to_embedding_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json at all")

    _assert_embedding_error(_provider(httpx.MockTransport(handler)), "malformed")


def test_transport_failure_maps_to_embedding_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    _assert_embedding_error(
        _provider(httpx.MockTransport(handler)), "transport", "ConnectError"
    )


def test_execution_bound_is_enforced_and_never_hangs() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(10)
        return httpx.Response(200, json=_vector_body([0.1]))

    provider = _provider(httpx.MockTransport(handler), timeout_seconds=0.05)
    _assert_embedding_error(provider, "execution bound")


# ---------------------------------------------------------------- key hygiene


def test_missing_key_is_an_explicit_configuration_error() -> None:
    saved = os.environ.pop("GOOGLE_API_KEY", None)
    try:
        with pytest.raises(SecretNotFoundError) as excinfo:
            GeminiEmbeddingProvider(_settings(), EnvironmentSecretProvider())
        assert excinfo.value.code == "secret.not_found"
        assert "GOOGLE_API_KEY" in str(excinfo.value)
    finally:
        if saved is not None:
            os.environ["GOOGLE_API_KEY"] = saved
