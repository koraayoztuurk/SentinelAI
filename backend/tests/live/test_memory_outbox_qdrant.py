"""Live outbox → projector → Qdrant tests (ES-050, ADR-012).

Opt-in (`pytest -m live_qdrant`): runs against a real PostgreSQL (outbox +
Memory Items) and a real Qdrant (derived embeddings) with a **fake
deterministic embedder** (no provider key, CI-able). Verifies the ES-050 exit
criteria — the transactional outbox is written with the Memory Item, the
projector drains it into Qdrant, projection is **idempotent** (two projections
of the same item leave exactly one point), and an embedding failure is isolated
(record marked failed, no point, Memory Item intact).
"""

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.application.memory import MemoryEmbeddingError
from app.application.memory.projector import MemoryEmbeddingProjector
from app.domain.identifiers import MemoryItemId
from app.infrastructure.persistence.postgres.engine import create_session_factory
from app.infrastructure.persistence.postgres.memory.outbox_repository import (
    PostgresOutboxRepository,
)
from app.infrastructure.persistence.postgres.memory.repositories import (
    PostgresMemoryRepository,
)
from app.infrastructure.persistence.postgres.session import session_scope
from app.infrastructure.persistence.qdrant.memory_vector_store import (
    COLLECTION_NAME,
    QdrantMemoryVectorStore,
)
from tests.live.qdrant_support import clear_collection, live_qdrant_client
from tests.live.support import ensure_schema, live_engine
from tests.support.builders import build_memory_item

pytestmark = pytest.mark.live_qdrant

_DIM = 3


class _FakeEmbedder:
    """Deterministic in-test embedder (no provider key needed)."""

    def __init__(self, fail: bool = False) -> None:
        self._fail = fail

    async def embed(self, text: str) -> tuple[float, ...]:
        if self._fail:
            raise MemoryEmbeddingError("embedding unavailable")
        return (0.1, 0.2, 0.3)


async def _reset(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE TABLE memory_outbox, memory_item CASCADE")
        )


async def _pending_count(factory: object) -> int:
    async with session_scope(factory) as session:  # type: ignore[arg-type]
        return len(await PostgresOutboxRepository(session).list_pending(100))


def test_outbox_projection_is_idempotent_single_point() -> None:
    ensure_schema()
    asyncio.run(_idempotency_scenario())


async def _idempotency_scenario() -> None:
    engine = live_engine()
    qdrant = live_qdrant_client()
    try:
        await _reset(engine)
        await clear_collection(qdrant)
        factory = create_session_factory(engine)
        store = QdrantMemoryVectorStore(qdrant)
        await store.ensure_collection(_DIM)

        # Two versions of one Memory Item → two outbox intents, both written in
        # the same transaction as their memory row.
        async with session_scope(factory) as session:
            repo = PostgresMemoryRepository(session)
            await repo.add(build_memory_item("mq-1", version=1, content="alpha"))
            await repo.add(build_memory_item("mq-1", version=2, content="beta"))

        # Draining both intents upserts the same deterministic point id.
        async with session_scope(factory) as session:
            processed = await MemoryEmbeddingProjector(
                PostgresOutboxRepository(session),
                PostgresMemoryRepository(session),
                _FakeEmbedder(),
                store,
            ).project_pending()
        assert processed == 2

        # Idempotent: exactly one Qdrant point for the item; outbox drained.
        count = (await qdrant.count(collection_name=COLLECTION_NAME)).count
        assert count == 1
        assert await _pending_count(factory) == 0
    finally:
        await qdrant.close()
        await engine.dispose()


def test_embedding_failure_isolated_record_failed_memory_intact() -> None:
    ensure_schema()
    asyncio.run(_failure_scenario())


async def _failure_scenario() -> None:
    engine = live_engine()
    qdrant = live_qdrant_client()
    try:
        await _reset(engine)
        await clear_collection(qdrant)
        factory = create_session_factory(engine)
        store = QdrantMemoryVectorStore(qdrant)
        await store.ensure_collection(_DIM)

        async with session_scope(factory) as session:
            await PostgresMemoryRepository(session).add(
                build_memory_item("mq-fail", version=1, content="x")
            )

        async with session_scope(factory) as session:
            processed = await MemoryEmbeddingProjector(
                PostgresOutboxRepository(session),
                PostgresMemoryRepository(session),
                _FakeEmbedder(fail=True),
                store,
            ).project_pending()
        assert processed == 0

        # No Qdrant point; the Memory Item is untouched.
        count = (await qdrant.count(collection_name=COLLECTION_NAME)).count
        assert count == 0
        async with session_scope(factory) as session:
            item = await PostgresMemoryRepository(session).get(
                MemoryItemId("mq-fail")
            )
        assert item is not None
        assert item.content == "x"
        # The failed record is no longer pending (marked failed).
        assert await _pending_count(factory) == 0
    finally:
        await qdrant.close()
        await engine.dispose()
