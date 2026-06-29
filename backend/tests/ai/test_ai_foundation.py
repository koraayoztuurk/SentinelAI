"""Unit tests for the AI Foundation (ES-009).

Plain pytest functions. The provider ports are interfaces only; tiny in-test
fakes prove the contracts are usable and structurally satisfiable. No live AI
calls.
"""

import asyncio
import dataclasses

import pytest

from app.ai import (
    AIRuntimeError,
    EmbeddingProvider,
    EmbeddingProviderError,
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
)
from app.shared.exceptions import SentinelAIError


class _FakeLLM:
    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=f"echo:{request.prompt}")


class _FakeEmbedding:
    async def embed(self, text: str) -> tuple[float, ...]:
        return (float(len(text)), 0.0)


def test_llm_provider_is_protocol() -> None:
    assert getattr(LLMProvider, "_is_protocol", False) is True


def test_embedding_provider_is_protocol() -> None:
    assert getattr(EmbeddingProvider, "_is_protocol", False) is True


def test_llm_request_and_response_are_frozen() -> None:
    request = LLMRequest(prompt="hello")
    response = LLMResponse(text="hi")
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.prompt = "x"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        response.text = "y"  # type: ignore[misc]


def test_fake_llm_satisfies_contract() -> None:
    async def scenario() -> None:
        provider: LLMProvider = _FakeLLM()
        result = await provider.generate(LLMRequest(prompt="ping"))
        assert isinstance(result, LLMResponse)
        assert result.text == "echo:ping"

    asyncio.run(scenario())


def test_fake_embedding_satisfies_contract() -> None:
    async def scenario() -> None:
        provider: EmbeddingProvider = _FakeEmbedding()
        vector = await provider.embed("abc")
        assert vector == (3.0, 0.0)

    asyncio.run(scenario())


def test_error_hierarchy_and_codes() -> None:
    assert issubclass(AIRuntimeError, SentinelAIError)
    assert issubclass(LLMProviderError, AIRuntimeError)
    assert issubclass(EmbeddingProviderError, AIRuntimeError)
    assert AIRuntimeError.code == "ai.error"
    assert LLMProviderError.code == "ai.llm_provider_error"
    assert EmbeddingProviderError.code == "ai.embedding_provider_error"
