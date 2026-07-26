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
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.ai.agents.memory.plan import (
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalStrategy,
)
from app.ai.agents.planner.state import InvestigationState
from app.application.memory import (
    MemoryEmbeddingError,
    MemoryService,
    OutboxRecord,
)
from app.application.memory.projector import (
    MemoryEmbeddingProjector,
    ProjectionOutcome,
    ProjectionRetryPolicy,
)
from app.domain.enums import MemoryStatus
from app.domain.erasure import REDACTED
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
    QdrantMemoryVectorStore,
)
from tests.live.qdrant_support import (
    TEST_COLLECTION_NAME,
    clear_collection,
    live_qdrant_client,
)
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


async def _due_count(factory: object) -> int:
    async with session_scope(factory) as session:  # type: ignore[arg-type]
        return len(await PostgresOutboxRepository(session).list_due(100))


async def _dead_letter_count(factory: object) -> int:
    async with session_scope(factory) as session:  # type: ignore[arg-type]
        return await PostgresOutboxRepository(session).count_dead_letters()


async def _one_record(factory: object) -> OutboxRecord:
    """The single due record the retry tests operate on."""

    async with session_scope(factory) as session:  # type: ignore[arg-type]
        (record,) = await PostgresOutboxRepository(session).list_due(100)
        return record


async def _project(
    session: AsyncSession,
    store: QdrantMemoryVectorStore,
    policy: ProjectionRetryPolicy,
    fail: bool,
) -> ProjectionOutcome:
    """One projection cycle over the live stores with the given policy."""

    return await MemoryEmbeddingProjector(
        PostgresOutboxRepository(session),
        PostgresMemoryRepository(session),
        _FakeEmbedder(fail=fail),
        store,
        policy,
    ).project_pending()


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
        store = QdrantMemoryVectorStore(qdrant, TEST_COLLECTION_NAME)
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
        assert processed.processed == 2

        # Idempotent: exactly one Qdrant point for the item; outbox drained.
        count = (await qdrant.count(collection_name=TEST_COLLECTION_NAME)).count
        assert count == 1
        assert await _due_count(factory) == 0
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
        store = QdrantMemoryVectorStore(qdrant, TEST_COLLECTION_NAME)
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
        assert processed.processed == 2

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


def test_memory_erasure_deletes_the_projected_point() -> None:
    ensure_schema()
    asyncio.run(_erasure_scenario())


async def _erasure_scenario() -> None:
    """ES-065: erasing a Memory Item drops its derived point (ES-050 TD closed).

    The full end-of-life propagation over live stores: erase writes the
    tombstoned versions **and** the erasure intent in one PostgreSQL
    transaction, and the projector drains that intent into a Qdrant point
    deletion (ADR-012 reused for erasure, ADR-017 §5).
    """

    engine = live_engine()
    qdrant = live_qdrant_client()
    try:
        await _reset(engine)
        await clear_collection(qdrant)
        factory = create_session_factory(engine)
        store = QdrantMemoryVectorStore(qdrant, TEST_COLLECTION_NAME)
        await store.ensure_collection(_DIM)

        # A projected Memory Item: one point exists.
        async with session_scope(factory) as session:
            await PostgresMemoryRepository(session).add(
                build_memory_item("mq-e", version=1, content="jane.doe notes")
            )
        async with session_scope(factory) as session:
            await MemoryEmbeddingProjector(
                PostgresOutboxRepository(session),
                PostgresMemoryRepository(session),
                _FakeEmbedder(),
                store,
            ).project_pending()
        assert (await qdrant.count(collection_name=TEST_COLLECTION_NAME)).count == 1

        # Erase through the service: tombstone + erasure intent, one store.
        async with session_scope(factory) as session:
            erased = await MemoryService(
                PostgresMemoryRepository(session)
            ).erase(MemoryItemId("mq-e"))
        assert erased.status is MemoryStatus.ERASED
        assert erased.content == REDACTED

        # Draining the intent deletes the derived point.
        async with session_scope(factory) as session:
            processed = await MemoryEmbeddingProjector(
                PostgresOutboxRepository(session),
                PostgresMemoryRepository(session),
                _FakeEmbedder(),
                store,
            ).project_pending()
        assert processed.processed == 1
        assert (await qdrant.count(collection_name=TEST_COLLECTION_NAME)).count == 0
        assert await _due_count(factory) == 0

        # Every persisted version is redacted, not just the latest.
        async with session_scope(factory) as session:
            versions = await PostgresMemoryRepository(session).list_versions(
                MemoryItemId("mq-e")
            )
        assert versions
        assert all(v.content == REDACTED for v in versions)
        assert all(v.status is MemoryStatus.ERASED for v in versions)
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
        store = QdrantMemoryVectorStore(qdrant, TEST_COLLECTION_NAME)
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
        assert processed == ProjectionOutcome(retried=1)

        # No Qdrant point; the Memory Item is untouched.
        count = (await qdrant.count(collection_name=TEST_COLLECTION_NAME)).count
        assert count == 0
        async with session_scope(factory) as session:
            item = await PostgresMemoryRepository(session).get(
                MemoryItemId("mq-fail")
            )
        assert item is not None
        assert item.content == "x"
        # ES-067: the record is not gone, it is *backing off* — it stays
        # pending but is not due yet, so the next cycle skips it.
        assert await _due_count(factory) == 0
        assert await _dead_letter_count(factory) == 0
    finally:
        await qdrant.close()
        await engine.dispose()


def test_backed_off_record_leaves_and_re_enters_the_due_set() -> None:
    """ES-067 over live PostgreSQL: the retry schedule, on the database clock.

    Closes the ES-050 deferral ("a failed record stays failed and is not
    auto-retried") and exercises migration 0006's ``next_attempt_at``. The
    delays are chosen so the assertions never race a wall-clock boundary: a
    long backoff must hold the record back, a zero backoff must release it.
    """

    ensure_schema()
    asyncio.run(_retry_schedule_scenario())


async def _retry_schedule_scenario() -> None:
    engine = live_engine()
    qdrant = live_qdrant_client()
    try:
        await _reset(engine)
        await clear_collection(qdrant)
        factory = create_session_factory(engine)
        store = QdrantMemoryVectorStore(qdrant, TEST_COLLECTION_NAME)
        await store.ensure_collection(_DIM)

        async with session_scope(factory) as session:
            await PostgresMemoryRepository(session).add(
                build_memory_item("mq-retry", version=1, content="x")
            )
        assert await _due_count(factory) == 1
        # Captured while the record is still due — after the next step it is
        # deliberately held back, so it cannot be looked up through list_due.
        seq = (await _one_record(factory)).seq

        # A minute of backoff: the record must drop out of the due set, and no
        # plausible test-execution delay can bring it back.
        patient = ProjectionRetryPolicy(
            max_attempts=5, backoff_base_seconds=60.0, backoff_max_seconds=60.0
        )
        async with session_scope(factory) as session:
            outcome = await _project(session, store, patient, fail=True)
        assert outcome == ProjectionOutcome(retried=1)
        assert await _due_count(factory) == 0
        assert await _dead_letter_count(factory) == 0

        # Rescheduling with no backoff releases it again — the store decides
        # due-ness from the deadline it stored, not from the app's clock.
        immediate = ProjectionRetryPolicy(
            max_attempts=5, backoff_base_seconds=0.0, backoff_max_seconds=0.0
        )
        async with session_scope(factory) as session:
            await PostgresOutboxRepository(session).mark_retry(
                seq, "reset for the next attempt", 0.0
            )
        assert await _due_count(factory) == 1

        # A recovered provider projects the very same record (idempotence is
        # what makes retrying safe at all — ADR-012).
        async with session_scope(factory) as session:
            outcome = await _project(session, store, immediate, fail=False)
        assert outcome == ProjectionOutcome(processed=1)
        assert (await qdrant.count(collection_name=TEST_COLLECTION_NAME)).count == 1
        assert await _due_count(factory) == 0
    finally:
        await qdrant.close()
        await engine.dispose()


def test_record_dead_letters_once_its_budget_is_spent() -> None:
    """The terminal, observable end of a hopeless record (ES-067).

    Uses a zero backoff so the schedule never gates the assertions: what is
    under test is the attempt accounting, and that the Memory Item survives
    its embedding being abandoned.
    """

    ensure_schema()
    asyncio.run(_dead_letter_scenario())


async def _dead_letter_scenario() -> None:
    engine = live_engine()
    qdrant = live_qdrant_client()
    try:
        await _reset(engine)
        await clear_collection(qdrant)
        factory = create_session_factory(engine)
        store = QdrantMemoryVectorStore(qdrant, TEST_COLLECTION_NAME)
        await store.ensure_collection(_DIM)
        policy = ProjectionRetryPolicy(
            max_attempts=3, backoff_base_seconds=0.0, backoff_max_seconds=0.0
        )

        async with session_scope(factory) as session:
            await PostgresMemoryRepository(session).add(
                build_memory_item("mq-dead", version=1, content="x")
            )

        # Two failures inside the budget: rescheduled, still in the working set.
        for _ in range(2):
            async with session_scope(factory) as session:
                outcome = await _project(session, store, policy, fail=True)
            assert outcome == ProjectionOutcome(retried=1)
            assert await _due_count(factory) == 1
            assert await _dead_letter_count(factory) == 0

        # The third spends the budget: terminal, and no longer picked up.
        async with session_scope(factory) as session:
            outcome = await _project(session, store, policy, fail=True)
        assert outcome == ProjectionOutcome(dead_lettered=1)
        assert await _due_count(factory) == 0
        assert await _dead_letter_count(factory) == 1

        # ADR-012: the derived representation was abandoned, the authoritative
        # Memory Item was not.
        async with session_scope(factory) as session:
            item = await PostgresMemoryRepository(session).get(
                MemoryItemId("mq-dead")
            )
        assert item is not None
        assert item.content == "x"
        assert (await qdrant.count(collection_name=TEST_COLLECTION_NAME)).count == 0
    finally:
        await qdrant.close()
        await engine.dispose()
