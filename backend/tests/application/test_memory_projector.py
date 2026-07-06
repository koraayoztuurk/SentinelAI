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

    async def ensure_collection(self, dimensions: int) -> None:
        pass

    async def upsert(
        self, memory_id: str, vector: tuple[float, ...], payload: object
    ) -> None:
        # Keyed by memory_id → re-upsert replaces the single point (idempotent).
        self.points[memory_id] = vector


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
