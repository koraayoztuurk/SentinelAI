"""Memory vector-store contract (ADR-012, ES-050).

The narrow port through which the embedding projector writes derived Memory
Item embeddings to the Vector Database — the projector's only outbound seam to
the vector store, keeping it free of infrastructure imports (the concrete
Qdrant adapter implements this port).

Idempotence (ADR-012): ``upsert`` is keyed by ``memory_id`` alone, so
re-projecting the same Memory Item always yields the same single point
(the latest version's embedding replaces any prior one).
"""

from collections.abc import Mapping
from typing import Protocol


class MemoryVectorStore(Protocol):
    """Writes derived Memory Item embeddings to the vector store."""

    async def ensure_collection(self, dimensions: int) -> None:
        """Create the memory-embeddings collection if it does not exist."""
        ...

    async def upsert(
        self,
        memory_id: str,
        vector: tuple[float, ...],
        payload: Mapping[str, object],
    ) -> None:
        """Insert or replace the single embedding point for a Memory Item."""
        ...
