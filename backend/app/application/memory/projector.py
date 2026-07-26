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
  authoritative Memory Item; the record is rescheduled or dead-lettered and
  remains observable (embedding failures should not corrupt Memory Items —
  memory-service).
- **Bounded retry (ES-067)** — a failed record is retried with exponential
  backoff up to the policy's attempt budget, then dead-lettered into a
  terminal, observable state. This closes the ES-050 deferral (a failed record
  used to stay ``failed``, never auto-retried). Retry is safe precisely because
  projection is idempotent.
- **No layer violation** — depends only on application ports (outbox, memory
  repository, embedder, vector store); the concrete Qdrant/Gemini adapters are
  injected. The backoff *delay* is computed here but applied by the adapter,
  which owns the clock (services read no clock).

The projector re-reads the latest Memory Item to obtain the embeddable text
(``content``; a blank content falls back to the type so a point always exists),
so the outbox carries identifiers only.
"""

import logging
from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class ProjectionRetryPolicy:
    """How many times a failed projection is retried, and how far apart.

    Values are configuration supplied by the composition root (ES-067). The
    defaults are deliberately patient rather than aggressive: the projector runs
    in the background, so a slow recovery costs nothing but a delayed embedding,
    while a tight loop against a rate-limited provider costs quota.
    """

    max_attempts: int = 5
    backoff_base_seconds: float = 5.0
    backoff_max_seconds: float = 300.0

    def delay_for(self, attempts: int) -> float:
        """Backoff before the next attempt, given failures so far (1-based)."""

        exponential = self.backoff_base_seconds * 2.0 ** max(0, attempts - 1)
        return min(exponential, self.backoff_max_seconds)

    def is_exhausted(self, attempts: int) -> bool:
        """Whether ``attempts`` failures have spent the retry budget."""

        return attempts >= max(1, self.max_attempts)


@dataclass(frozen=True, slots=True)
class ProjectionOutcome:
    """What one projection cycle did (operational visibility, ES-067).

    Returned to the composition root, which owns metrics — the application
    layer stays free of observability wiring.
    """

    processed: int = 0
    retried: int = 0
    dead_lettered: int = 0


class MemoryEmbeddingProjector:
    """Drains the outbox into the vector store (idempotent)."""

    def __init__(
        self,
        outbox: OutboxRepository,
        memory: MemoryRepository,
        embedder: MemoryEmbedder,
        vector_store: MemoryVectorStore,
        retry_policy: ProjectionRetryPolicy | None = None,
    ) -> None:
        self._outbox = outbox
        self._memory = memory
        self._embedder = embedder
        self._vector_store = vector_store
        self._retry = retry_policy or ProjectionRetryPolicy()

    async def project_pending(self, limit: int = 100) -> ProjectionOutcome:
        """Project every due record once; report what the cycle did."""

        due = await self._outbox.list_due(limit)
        processed = retried = dead_lettered = 0
        for record in due:
            if await self._project_one(record):
                processed += 1
            elif self._retry.is_exhausted(record.attempts + 1):
                dead_lettered += 1
            else:
                retried += 1
        return ProjectionOutcome(processed, retried, dead_lettered)

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
            await self._handle_failure(record, exc)
            return False

    async def _handle_failure(
        self, record: OutboxRecord, exc: Exception
    ) -> None:
        """Reschedule the record, or retire it once the budget is spent."""

        attempts = record.attempts + 1
        code = getattr(exc, "code", "unknown")
        if self._retry.is_exhausted(attempts):
            await self._outbox.mark_dead_letter(record.seq, str(exc))
            # Loud on purpose: the Memory Item is intact but has no embedding,
            # so it is invisible to semantic retrieval until an operator acts.
            logger.error(
                "memory embedding dead-lettered memory_id=%s attempts=%s code=%s",
                record.memory_id,
                attempts,
                code,
            )
            return
        delay = self._retry.delay_for(attempts)
        await self._outbox.mark_retry(record.seq, str(exc), delay)
        logger.warning(
            "memory embedding projection failed memory_id=%s attempts=%s "
            "retry_in=%.1fs code=%s",
            record.memory_id,
            attempts,
            delay,
            code,
        )
