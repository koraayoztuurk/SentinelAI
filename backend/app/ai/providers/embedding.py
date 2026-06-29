"""Embedding provider port.

Defines the provider-neutral embedding interface the AI Runtime depends on
(ADR-005, agent-architecture §6a). It is intentionally **single-text**: batch
embedding is intentionally deferred until a consumer requires it.

This contract must remain entirely provider-neutral. It must not expose OpenAI-,
Anthropic-, Gemini- or any other vendor-specific concepts, parameters or types.
Concrete providers are introduced by later specifications.
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Replaceable embedding provider interface (single-text)."""

    async def embed(self, text: str) -> tuple[float, ...]: ...
