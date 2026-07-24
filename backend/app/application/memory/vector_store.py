"""Memory vector-store contract (ADR-012, ES-050/ES-051).

The narrow port over the Vector Database's derived Memory Item embeddings:
the embedding projector **writes** through it (its only outbound seam to the
vector store, ES-050) and semantic retrieval **reads** through it (ES-051).
Both sides stay free of infrastructure imports (the concrete Qdrant adapter
implements this port).

Idempotence (ADR-012): ``upsert`` is keyed by ``memory_id`` alone, so
re-projecting the same Memory Item always yields the same single point
(the latest version's embedding replaces any prior one).

``search`` returns similarity matches over the derived representation only:
the authoritative Memory Item content is never stored here — consumers map a
match back to the system of record through ``memory_id`` (database-architecture
§8a: identifiers are the only cross-store reference mechanism).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class MemoryVectorMatch:
    """One similarity match from the derived embedding store.

    ``score`` is the store's similarity measure (cosine similarity here:
    higher is more similar). ``payload`` carries the projected identifying
    metadata (memory id, version, type, source investigation id) — never the
    authoritative content.
    """

    memory_id: str
    score: float
    payload: Mapping[str, object]


class MemoryVectorStore(Protocol):
    """Reads and writes derived Memory Item embeddings in the vector store."""

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

    async def search(
        self, vector: tuple[float, ...], limit: int
    ) -> tuple[MemoryVectorMatch, ...]:
        """Return the most similar Memory Item points, best first.

        An absent collection yields an empty result (nothing has been
        projected yet), never an error.
        """
        ...

    async def delete(self, memory_id: str) -> None:
        """Delete a Memory Item's embedding point (ES-065, ADR-017 §5/§6).

        Derived data is erased with its source (data-lifecycle.md §3): when a
        Memory Item is erased, the projector deletes its point through this
        seam. Keyed by ``memory_id`` like ``upsert``, and idempotent — deleting
        an absent point (or an absent collection) is a no-op, so the erasure
        projection is safely retriable.
        """
        ...
