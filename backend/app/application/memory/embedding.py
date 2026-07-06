"""Memory Service embedding port (ADR-012 §3).

The Memory Service owns the production of its Memory Item embeddings (the only
derived representation in the architecture, database-architecture §7). ADR-012
resolves audit finding D-01 by placing a **narrow embedding port in the Memory
Service's own application layer** and its implementation in the infrastructure
layer — so the Memory Service never depends on the AI Runtime (AC-04), while
the concrete adapter may internally use the AI Runtime's provider-neutral
embedding provider or call a provider directly.

This module defines that application-owned port. It is provider-neutral: it
exposes no Gemini/OpenAI/vendor concepts. The concrete adapter (infrastructure)
and the outbox projector that consumes it are introduced by later
specifications (ES-050).

Resilience: an embedding failure is surfaced as :class:`MemoryEmbeddingError`
with a stable code, never as an unmapped provider exception; the projector
contains it and leaves the outbox record unprocessed for retry (ADR-012).
"""

from typing import Protocol

from app.application.memory.errors import MemoryServiceError


class MemoryEmbeddingError(MemoryServiceError):
    """Raised when producing a Memory Item embedding fails."""

    code = "memory.embedding_error"


class MemoryEmbedder(Protocol):
    """Produces the embedding vector for a Memory Item's text (single-text).

    Implemented by the infrastructure layer. Batch embedding is deferred until
    a consumer requires it (mirrors the AI Runtime embedding port).
    """

    async def embed(self, text: str) -> tuple[float, ...]: ...
