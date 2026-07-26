"""Tests for the memory embedding projector (ES-050, ADR-012; ES-067 retry).

Deterministic, in-memory validation of the projector's contract with fake
ports (no Postgres/Qdrant): due records are embedded and upserted then
marked processed; an embedding failure is isolated (the Memory Item untouched)
and rescheduled with backoff until the budget is spent, when the record is
dead-lettered; the embed text comes from ``content`` with a type fallback;
idempotence is exercised through the deterministic upsert key.
"""

import asyncio

from app.application.memory import MemoryEmbeddingError, OutboxRecord
from app.application.memory.projector import (
    MemoryEmbeddingProjector,
    ProjectionOutcome,
    ProjectionRetryPolicy,
    embedding_text,
)
from app.domain.enums import MemoryStatus
from app.domain.erasure import REDACTED
from app.domain.identifiers import MemoryItemId
from app.domain.memory_item import MemoryItem
from tests.support.builders import build_memory_item


class _FakeOutbox:
    def __init__(self, records: list[OutboxRecord]) -> None:
        self._records = records
        self.processed: list[int] = []
        self.retried: list[tuple[int, str, float]] = []
        self.dead_lettered: list[tuple[int, str]] = []

    async def list_due(self, limit: int) -> tuple[OutboxRecord, ...]:
        return tuple(self._records[:limit])

    async def mark_processed(self, seq: int) -> None:
        self.processed.append(seq)

    async def mark_retry(
        self, seq: int, error: str, delay_seconds: float
    ) -> None:
        self.retried.append((seq, error, delay_seconds))

    async def mark_dead_letter(self, seq: int, error: str) -> None:
        self.dead_lettered.append((seq, error))


class _FakeMemory:
    def __init__(self, items: dict[str, MemoryItem]) -> None:
        self._items = items

    async def get(self, memory_id: MemoryItemId) -> MemoryItem | None:
        return self._items.get(memory_id.value)


class _FakeEmbedder:
    def __init__(self, fail: bool = False) -> None:
        self._fail = fail
        self.calls: list[str] = []

    async def embed(self, text: str) -> tuple[float, ...]:
        self.calls.append(text)
        if self._fail:
            raise MemoryEmbeddingError("embedding unavailable")
        return (0.1, 0.2, 0.3)


class _FakeVectorStore:
    def __init__(self) -> None:
        self.points: dict[str, tuple[float, ...]] = {}
        self.deleted: list[str] = []

    async def ensure_collection(self, dimensions: int) -> None:
        pass

    async def upsert(
        self, memory_id: str, vector: tuple[float, ...], payload: object
    ) -> None:
        # Keyed by memory_id → re-upsert replaces the single point (idempotent).
        self.points[memory_id] = vector

    async def delete(self, memory_id: str) -> None:
        # Idempotent, like the real adapter: deleting an absent point is a no-op.
        self.deleted.append(memory_id)
        self.points.pop(memory_id, None)


def _projector(
    outbox: _FakeOutbox,
    memory: _FakeMemory,
    embedder: _FakeEmbedder,
    store: _FakeVectorStore,
    retry: ProjectionRetryPolicy | None = None,
) -> MemoryEmbeddingProjector:
    return MemoryEmbeddingProjector(outbox, memory, embedder, store, retry)


def test_embedding_text_prefers_content_then_type() -> None:
    with_content = build_memory_item("m1", content="Lateral movement summary")
    assert embedding_text(with_content) == "Lateral movement summary"
    blank = build_memory_item("m2", type_value="beacon_pattern", content="  ")
    assert embedding_text(blank) == "beacon_pattern"


def test_project_pending_embeds_upserts_and_marks_processed() -> None:
    item = build_memory_item("m1", content="ransomware playbook")
    outbox = _FakeOutbox([OutboxRecord(seq=1, memory_id="m1", memory_version=1)])
    embedder = _FakeEmbedder()
    store = _FakeVectorStore()
    projector = _projector(outbox, _FakeMemory({"m1": item}), embedder, store)

    outcome = asyncio.run(projector.project_pending())

    assert outcome == ProjectionOutcome(processed=1)
    assert embedder.calls == ["ransomware playbook"]
    assert store.points["m1"] == (0.1, 0.2, 0.3)
    assert outbox.processed == [1]
    assert outbox.retried == []


def test_erased_memory_item_deletes_its_point_instead_of_embedding() -> None:
    # ES-065 / ADR-017 §5: derived data is erased with its source through the
    # same propagation that created it. The projector re-reads the item, sees
    # the terminal ERASED status and deletes the point — no embedding call.
    erased = build_memory_item(
        "m1", content=REDACTED, status=MemoryStatus.ERASED
    )
    outbox = _FakeOutbox([OutboxRecord(seq=3, memory_id="m1", memory_version=2)])
    embedder = _FakeEmbedder()
    store = _FakeVectorStore()
    store.points["m1"] = (0.5, 0.5, 0.5)
    projector = _projector(outbox, _FakeMemory({"m1": erased}), embedder, store)

    outcome = asyncio.run(projector.project_pending())

    assert outcome == ProjectionOutcome(processed=1)
    assert store.deleted == ["m1"]
    assert "m1" not in store.points
    # The redacted text is never sent to the embedding provider.
    assert embedder.calls == []
    assert outbox.processed == [3]
    assert outbox.retried == []


def test_erasure_projection_is_idempotent() -> None:
    erased = build_memory_item(
        "m1", content=REDACTED, status=MemoryStatus.ERASED
    )
    store = _FakeVectorStore()
    for seq in (4, 5):
        outbox = _FakeOutbox(
            [OutboxRecord(seq=seq, memory_id="m1", memory_version=2)]
        )
        projector = _projector(
            outbox, _FakeMemory({"m1": erased}), _FakeEmbedder(), store
        )
        assert asyncio.run(projector.project_pending()) == ProjectionOutcome(
            processed=1
        )
        assert outbox.processed == [seq]

    # Re-running settles the same way; the point stays gone.
    assert store.deleted == ["m1", "m1"]
    assert store.points == {}


def test_embedding_failure_is_isolated_and_rescheduled() -> None:
    item = build_memory_item("m1", content="x")
    outbox = _FakeOutbox([OutboxRecord(seq=7, memory_id="m1", memory_version=1)])
    store = _FakeVectorStore()
    projector = _projector(
        outbox, _FakeMemory({"m1": item}), _FakeEmbedder(fail=True), store
    )

    outcome = asyncio.run(projector.project_pending())

    assert outcome == ProjectionOutcome(retried=1)
    assert outbox.retried and outbox.retried[0][0] == 7
    assert outbox.dead_lettered == []
    assert outbox.processed == []
    # The vector store was never written (Memory Item derived state untouched).
    assert store.points == {}


def test_reprojection_is_idempotent_single_point() -> None:
    item = build_memory_item("m1", content="one")
    store = _FakeVectorStore()
    for _ in range(2):
        outbox = _FakeOutbox(
            [OutboxRecord(seq=1, memory_id="m1", memory_version=1)]
        )
        projector = _projector(
            outbox, _FakeMemory({"m1": item}), _FakeEmbedder(), store
        )
        asyncio.run(projector.project_pending())

    # Two projections of the same item leave exactly one point.
    assert list(store.points.keys()) == ["m1"]


def test_missing_memory_item_settles_the_record() -> None:
    outbox = _FakeOutbox(
        [OutboxRecord(seq=3, memory_id="gone", memory_version=1)]
    )
    store = _FakeVectorStore()
    projector = _projector(outbox, _FakeMemory({}), _FakeEmbedder(), store)

    outcome = asyncio.run(projector.project_pending())

    assert outcome == ProjectionOutcome(processed=1)
    assert outbox.processed == [3]
    assert store.points == {}


# --------------------------------------------------- retry & dead-letter (ES-067)


def test_retry_backoff_grows_with_attempts_and_is_capped() -> None:
    policy = ProjectionRetryPolicy(
        max_attempts=10, backoff_base_seconds=5.0, backoff_max_seconds=20.0
    )

    # 1st failure waits the base delay, then it doubles per attempt...
    assert policy.delay_for(1) == 5.0
    assert policy.delay_for(2) == 10.0
    assert policy.delay_for(3) == 20.0
    # ...and never exceeds the ceiling, so a long outage cannot push the next
    # attempt beyond a bounded horizon.
    assert policy.delay_for(9) == 20.0


def test_failure_carries_the_policy_delay_for_the_next_attempt() -> None:
    item = build_memory_item("m1", content="x")
    outbox = _FakeOutbox(
        # One failure already recorded: the next delay is the second step.
        [OutboxRecord(seq=7, memory_id="m1", memory_version=1, attempts=1)]
    )
    policy = ProjectionRetryPolicy(
        max_attempts=5, backoff_base_seconds=5.0, backoff_max_seconds=300.0
    )
    projector = _projector(
        outbox,
        _FakeMemory({"m1": item}),
        _FakeEmbedder(fail=True),
        _FakeVectorStore(),
        policy,
    )

    assert asyncio.run(projector.project_pending()) == ProjectionOutcome(retried=1)
    (seq, _error, delay) = outbox.retried[0]
    assert seq == 7
    assert delay == 10.0


def test_record_is_dead_lettered_once_the_budget_is_spent() -> None:
    item = build_memory_item("m1", content="x")
    outbox = _FakeOutbox(
        # Two failures already; with a budget of three, this attempt is the last.
        [OutboxRecord(seq=9, memory_id="m1", memory_version=1, attempts=2)]
    )
    projector = _projector(
        outbox,
        _FakeMemory({"m1": item}),
        _FakeEmbedder(fail=True),
        _FakeVectorStore(),
        ProjectionRetryPolicy(max_attempts=3),
    )

    outcome = asyncio.run(projector.project_pending())

    assert outcome == ProjectionOutcome(dead_lettered=1)
    assert outbox.dead_lettered and outbox.dead_lettered[0][0] == 9
    # Retired, not rescheduled: the record leaves the working set.
    assert outbox.retried == []


def test_dead_lettering_leaves_the_memory_item_untouched() -> None:
    # ADR-012: the derived representation is disposable, the Memory Item is not.
    # Giving up on the embedding must never damage the authoritative record.
    item = build_memory_item("m1", content="authoritative knowledge")
    outbox = _FakeOutbox(
        [OutboxRecord(seq=11, memory_id="m1", memory_version=1, attempts=4)]
    )
    memory = _FakeMemory({"m1": item})
    store = _FakeVectorStore()
    projector = _projector(
        outbox, memory, _FakeEmbedder(fail=True), store, ProjectionRetryPolicy()
    )

    asyncio.run(projector.project_pending())

    assert outbox.dead_lettered
    assert store.points == {}
    assert asyncio.run(memory.get(MemoryItemId("m1"))) is item


def test_a_recovered_provider_projects_a_previously_failed_record() -> None:
    # Retry is only worth having if it converges: the same record, once the
    # provider recovers, projects normally (projection is idempotent).
    item = build_memory_item("m1", content="late but projected")
    outbox = _FakeOutbox(
        [OutboxRecord(seq=13, memory_id="m1", memory_version=1, attempts=2)]
    )
    store = _FakeVectorStore()
    projector = _projector(
        outbox, _FakeMemory({"m1": item}), _FakeEmbedder(), store
    )

    assert asyncio.run(projector.project_pending()) == ProjectionOutcome(
        processed=1
    )
    assert outbox.processed == [13]
    assert store.points["m1"] == (0.1, 0.2, 0.3)
