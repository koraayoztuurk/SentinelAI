"""Memory embedding projector (ADR-012, ES-050).

The asynchronous, idempotent projector owned by the Memory Service's layer: it
drains pending outbox records, generates each Memory Item's embedding through
the application-owned embedding port and upserts it into the vector store. It is
the only producer of the derived embedding representation.

Guarantees (ADR-012):

- **Idempotent** — the vector store upsert is keyed by Memory Item id, so
  re-projecting the same record (retry, at-least-once delivery) yields the same
  single point. Marking a record processed after a successful upsert makes the
  derived state effectively-once.
- **Failure isolation** — an embedding or upsert failure never touches the
  authoritative Memory Item; the record is marked failed and remains observable
  for retry (embedding failures should not corrupt Memory Items — memory-service).
- **No layer violation** — depends only on application ports (outbox, memory
  repository, embedder, vector store); the concrete Qdrant/Gemini adapters are
  injected.

The projector re-reads the latest Memory Item to obtain the embeddable text
(``content``; a blank content falls back to the type so a point always exists),
so the outbox carries identifiers only.
"""

import logging

from app.application.memory.embedding import MemoryEmbedder, MemoryEmbeddingError
from app.application.memory.outbox import OutboxRecord, OutboxRepository
from app.application.memory.repositories import MemoryRepository
from app.application.memory.vector_store import MemoryVectorStore
from app.domain.enums import MemoryStatus
from app.domain.identifiers import MemoryItemId
from app.domain.memory_item import MemoryItem
from app.shared.exceptions import SentinelAIError

logger = logging.getLogger(__name__)


def embedding_text(item: MemoryItem) -> str:
    """The text embedded for a Memory Item (content; type as a safe fallback)."""

    return item.content.strip() or item.type.value


class MemoryEmbeddingProjector:
    """Drains the outbox into the vector store (idempotent)."""

    def __init__(
        self,
        outbox: OutboxRepository,
        memory: MemoryRepository,
        embedder: MemoryEmbedder,
        vector_store: MemoryVectorStore,
    ) -> None:
        self._outbox = outbox
        self._memory = memory
        self._embedder = embedder
        self._vector_store = vector_store

    async def project_pending(self, limit: int = 100) -> int:
        """Project all pending records once; return how many succeeded."""

        pending = await self._outbox.list_pending(limit)
        processed = 0
        for record in pending:
            if await self._project_one(record):
                processed += 1
        return processed

    async def _project_one(self, record: OutboxRecord) -> bool:
        try:
            item = await self._memory.get(MemoryItemId(record.memory_id))
            if item is None:
                # The Memory Item is gone; nothing to derive — settle the record.
                await self._outbox.mark_processed(record.seq)
                return True
            if item.status is MemoryStatus.ERASED:
                # End-of-life (ES-065): derived data is erased with its source
                # through the same propagation that created it (ADR-012 /
                # ADR-017 §5). Deletion is idempotent, so a retried record
                # settles the same way.
                await self._vector_store.delete(item.id.value)
                await self._outbox.mark_processed(record.seq)
                logger.info(
                    "memory embedding erased memory_id=%s", item.id.value
                )
                return True
            vector = await self._embedder.embed(embedding_text(item))
            await self._vector_store.upsert(
                item.id.value,
                vector,
                {
                    "memory_id": item.id.value,
                    "version": item.version,
                    "type": item.type.value,
                    "source_investigation_id": item.source_investigation_id.value,
                },
            )
            await self._outbox.mark_processed(record.seq)
            logger.info(
                "memory embedding projected memory_id=%s version=%s",
                item.id.value,
                item.version,
            )
            return True
        except (MemoryEmbeddingError, SentinelAIError) as exc:
            await self._outbox.mark_failed(record.seq, str(exc))
            logger.warning(
                "memory embedding projection failed memory_id=%s code=%s",
                record.memory_id,
                getattr(exc, "code", "unknown"),
            )
            return False
