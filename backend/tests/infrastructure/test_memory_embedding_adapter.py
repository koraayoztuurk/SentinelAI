"""Tests for the Memory-Service embedding bridge (ES-049, ADR-012 §3).

The infrastructure ``EmbeddingMemoryAdapter`` realizes the Memory Service's
application-owned ``MemoryEmbedder`` port by delegating to an AI Runtime
``EmbeddingProvider`` and translating the AI-layer ``EmbeddingProviderError``
into the memory port's stable ``MemoryEmbeddingError``. Verified with an
in-memory fake provider (no network). Plain functions, ``asyncio.run``.
"""

import asyncio

import pytest

from app.ai.errors import EmbeddingProviderError
from app.application.memory import MemoryEmbeddingError
from app.infrastructure.ai.memory_embedding import EmbeddingMemoryAdapter


class _FakeProvider:
    """AI Runtime EmbeddingProvider double."""

    def __init__(self, vector: tuple[float, ...] | None = None) -> None:
        self._vector = vector

    async def embed(self, text: str) -> tuple[float, ...]:
        if self._vector is None:
            raise EmbeddingProviderError("provider is unavailable")
        return self._vector


def test_delegates_and_returns_the_vector() -> None:
    adapter = EmbeddingMemoryAdapter(_FakeProvider((0.5, 0.25, 0.125)))
    vector = asyncio.run(adapter.embed("attack pattern text"))
    assert vector == (0.5, 0.25, 0.125)


def test_provider_error_is_translated_to_memory_error() -> None:
    adapter = EmbeddingMemoryAdapter(_FakeProvider(None))
    with pytest.raises(MemoryEmbeddingError) as excinfo:
        asyncio.run(adapter.embed("x"))
    # The memory port exposes its own stable code, not the AI-layer one.
    assert excinfo.value.code == "memory.embedding_error"
    # The originating provider code is preserved in the chained cause.
    assert isinstance(excinfo.value.__cause__, EmbeddingProviderError)
