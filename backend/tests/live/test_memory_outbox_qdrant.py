"""Live outbox → projector → Qdrant tests (ES-050/ES-051, ADR-012).

Opt-in (`pytest -m live_qdrant`): runs against a real PostgreSQL (outbox +
Memory Items) and a real Qdrant (derived embeddings) with a **fake
deterministic embedder** (no provider key, CI-able). Verifies the ES-050 exit
criteria — the transactional outbox is written with the Memory Item, the
projector drains it into Qdrant, projection is **idempotent** (two projections
of the same item leave exactly one point), and an embedding failure is isolated
(record marked failed, no point, Memory Item intact) — plus the ES-051
retrieval read path: projected knowledge is found again by semantic search and
mapped back to the authoritative Memory Item.
"""

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.ai.agents.memory.plan import (
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalStrategy,
)
from app.ai.agents.planner.state import InvestigationState
from app.application.memory import MemoryEmbeddingError, MemoryService
from app.application.memory.projector import MemoryEmbeddingProjector
from app.domain.identifiers import InvestigationId, MemoryItemId
from app.domain.value_objects import Confidence
from app.infrastructure.ai.retrieval import CompositeRetriever
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
from tests.support.builders import (
    build_memory_item,
    make_graph_service,
    make_investigation_service,
)

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


class _DirectionalEmbedder:
    """Text-sensitive deterministic embedder: distinct unit vectors per topic,
    so cosine ranking is meaningful without a provider key."""

    async def embed(self, text: str) -> tuple[float, ...]:
        if "beacon" in text:
            return (1.0, 0.0, 0.0)
        if "phishing" in text:
            return (0.0, 1.0, 0.0)
        return (0.0, 0.0, 1.0)


def test_semantic_retrieval_finds_projected_knowledge() -> None:
    ensure_schema()
    asyncio.run(_retrieval_scenario())


async def _retrieval_scenario() -> None:
    engine = live_engine()
    qdrant = live_qdrant_client()
    try:
        await _reset(engine)
        await clear_collection(qdrant)
        factory = create_session_factory(engine)
        store = QdrantMemoryVectorStore(qdrant)
        await store.ensure_collection(_DIM)
        embedder = _DirectionalEmbedder()

        # Two projected Memory Items on distinct topics.
        async with session_scope(factory) as session:
            repo = PostgresMemoryRepository(session)
            await repo.add(
                build_memory_item("mq-a", content="C2 beacon every 60s")
            )
            await repo.add(
                build_memory_item("mq-b", content="phishing kit reuse")
            )
        async with session_scope(factory) as session:
            processed = await MemoryEmbeddingProjector(
                PostgresOutboxRepository(session),
                PostgresMemoryRepository(session),
                embedder,
                store,
            ).project_pending()
        assert processed == 2

        # ES-051 read path: a beacon-topic query retrieves the beacon item
        # first, with content mapped back from the system of record.
        async with session_scope(factory) as session:
            retriever = CompositeRetriever(
                embedder,
                store,
                MemoryService(PostgresMemoryRepository(session)),
                make_investigation_service(),
                make_graph_service(),
            )
            state = InvestigationState(
                investigation_id=InvestigationId("inv-live"),
                status="active",
                confidence=Confidence(0.5),
                objectives=("Investigate: beacon traffic",),
            )
            knowledge = await retriever.retrieve(
                state,
                RetrievalPlan(
                    plan_id=RetrievalPlanId("plan-live"),
                    investigation_id=InvestigationId("inv-live"),
                    strategies=(RetrievalStrategy.SEMANTIC,),
                ),
            )

        assert knowledge.items, "semantic search returned no items"
        top = knowledge.items[0]
        assert top.reference == "mq-a"
        assert top.content == "C2 beacon every 60s"
        assert top.confidence.value >= knowledge.items[-1].confidence.value
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
