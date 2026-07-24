"""Tests for the memory embedding projector (ES-050, ADR-012).

Deterministic, in-memory validation of the projector's contract with fake
ports (no Postgres/Qdrant): pending records are embedded and upserted then
marked processed; an embedding failure is isolated (record marked failed, the
Memory Item untouched); the embed text comes from ``content`` with a type
fallback; idempotence is exercised through the deterministic upsert key.
"""

import asyncio

from app.application.memory import MemoryEmbeddingError, OutboxRecord
from app.application.memory.projector import (
    MemoryEmbeddingProjector,
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
        self.failed: list[tuple[int, str]] = []

    async def list_pending(self, limit: int) -> tuple[OutboxRecord, ...]:
        return tuple(self._records[:limit])

    async def mark_processed(self, seq: int) -> None:
        self.processed.append(seq)

    async def mark_failed(self, seq: int, error: str) -> None:
        self.failed.append((seq, error))


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
) -> MemoryEmbeddingProjector:
    return MemoryEmbeddingProjector(outbox, memory, embedder, store)


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

    count = asyncio.run(projector.project_pending())

    assert count == 1
    assert embedder.calls == ["ransomware playbook"]
    assert store.points["m1"] == (0.1, 0.2, 0.3)
    assert outbox.processed == [1]
    assert outbox.failed == []


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

    count = asyncio.run(projector.project_pending())

    assert count == 1
    assert store.deleted == ["m1"]
    assert "m1" not in store.points
    # The redacted text is never sent to the embedding provider.
    assert embedder.calls == []
    assert outbox.processed == [3]
    assert outbox.failed == []


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
        assert asyncio.run(projector.project_pending()) == 1
        assert outbox.processed == [seq]

    # Re-running settles the same way; the point stays gone.
    assert store.deleted == ["m1", "m1"]
    assert store.points == {}


def test_embedding_failure_is_isolated_record_marked_failed() -> None:
    item = build_memory_item("m1", content="x")
    outbox = _FakeOutbox([OutboxRecord(seq=7, memory_id="m1", memory_version=1)])
    store = _FakeVectorStore()
    projector = _projector(
        outbox, _FakeMemory({"m1": item}), _FakeEmbedder(fail=True), store
    )

    count = asyncio.run(projector.project_pending())

    assert count == 0
    assert outbox.failed and outbox.failed[0][0] == 7
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

    count = asyncio.run(projector.project_pending())

    assert count == 1
    assert outbox.processed == [3]
    assert store.points == {}
