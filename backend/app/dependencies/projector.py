"""Memory embedding projector background runner (ES-050).

The in-process asynchronous driver for the outbox projector (ADR-012
"asynchronous, idempotent projectors"). Composed at the root (it may see every
layer): it builds the concrete embedding provider (Gemini, via the
SecretProvider) and the Qdrant vector store from the persistence registry, then
polls :meth:`MemoryEmbeddingProjector.project_pending` on an interval.

Resilience: the loop tolerates store/provider outages — every cycle is wrapped
so a failure is logged and the loop continues (unprocessed outbox records stay
observable for the next cycle). A missing embedding key stops the runner cleanly
without breaking startup (memory writes still work; embeddings simply wait).
Cancelled on shutdown. Not started when disabled by settings (tests drive the
projector directly).
"""

import asyncio
import logging
from pathlib import Path

from app.application.investigation import EvidencePayloadErasureProjector
from app.application.memory.projector import MemoryEmbeddingProjector
from app.application.secrets import SecretNotFoundError
from app.config.ai import get_gemini_embedding_settings
from app.config.database import get_evidence_payload_settings
from app.config.settings import Settings
from app.infrastructure.ai.gemini_embedding import GeminiEmbeddingProvider
from app.infrastructure.ai.memory_embedding import EmbeddingMemoryAdapter
from app.infrastructure.objectstore.filesystem import (
    FilesystemEvidencePayloadStore,
)
from app.infrastructure.persistence.postgres.investigation.repositories import (
    PostgresEvidenceRepository,
)
from app.infrastructure.persistence.postgres.memory.outbox_repository import (
    PostgresOutboxRepository,
)
from app.infrastructure.persistence.postgres.memory.repositories import (
    PostgresMemoryRepository,
)
from app.infrastructure.persistence.postgres.session import session_scope
from app.infrastructure.persistence.qdrant.memory_vector_store import (
    QdrantMemoryVectorStore,
)
from app.infrastructure.persistence.registry import PersistenceRegistry
from app.infrastructure.secrets import EnvironmentSecretProvider

logger = logging.getLogger(__name__)


def start_outbox_projector(
    registry: PersistenceRegistry, settings: Settings
) -> asyncio.Task[None] | None:
    """Start the background projector task, or ``None`` when disabled."""

    if not settings.outbox_projector_enabled:
        return None
    return asyncio.create_task(_run(registry, settings))


def start_erasure_projector(
    registry: PersistenceRegistry, settings: Settings
) -> asyncio.Task[None] | None:
    """Start the payload erasure projector task, or ``None`` when disabled.

    Separate from the embedding projector on purpose: erasure must proceed even
    when no embedding provider key is configured (that loop exits early), and it
    touches the object store rather than the vector store.
    """

    if not settings.outbox_projector_enabled:
        return None
    return asyncio.create_task(_run_erasure(registry, settings))


async def _run_erasure(
    registry: PersistenceRegistry, settings: Settings
) -> None:
    payloads = FilesystemEvidencePayloadStore(
        Path(get_evidence_payload_settings().root)
    )
    while True:
        try:
            async with session_scope(registry.session_factory) as session:
                projector = EvidencePayloadErasureProjector(
                    PostgresEvidenceRepository(session), payloads
                )
                await projector.project_pending()
        except Exception as exc:  # noqa: BLE001 - best-effort background loop
            # Pending erasures keep their address and are retried next cycle;
            # CancelledError is a BaseException, so shutdown is not swallowed.
            logger.warning(
                "erasure projector cycle failed: %s", type(exc).__name__
            )
        await asyncio.sleep(settings.outbox_poll_interval_seconds)


async def _run(registry: PersistenceRegistry, settings: Settings) -> None:
    embedding_settings = get_gemini_embedding_settings()
    try:
        embedder = EmbeddingMemoryAdapter(
            GeminiEmbeddingProvider(embedding_settings, EnvironmentSecretProvider())
        )
    except SecretNotFoundError:
        logger.warning(
            "outbox projector not started: embedding key not configured"
        )
        return

    vector_store = QdrantMemoryVectorStore(registry.qdrant_client)
    collection_ready = False

    while True:
        try:
            if not collection_ready:
                await vector_store.ensure_collection(embedding_settings.dimensions)
                collection_ready = True
            async with session_scope(registry.session_factory) as session:
                projector = MemoryEmbeddingProjector(
                    PostgresOutboxRepository(session),
                    PostgresMemoryRepository(session),
                    embedder,
                    vector_store,
                )
                await projector.project_pending()
        except Exception as exc:  # noqa: BLE001 - best-effort background loop
            # Any store/provider outage is logged and retried next cycle (the
            # collection is re-ensured after a Qdrant blip). CancelledError is a
            # BaseException, so shutdown cancellation is not swallowed here.
            collection_ready = False
            logger.warning("outbox projector cycle failed: %s", type(exc).__name__)
        await asyncio.sleep(settings.outbox_poll_interval_seconds)
