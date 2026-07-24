"""Tests for Memory Item erasure (ES-065, ADR-017 §4).

The person-linked (right-to-be-forgotten) path for the shared knowledge layer:
erasure redacts the knowledge text of **every** version and marks them terminal
``ERASED`` — distinct from deprecation, which controls relevance rather than
existence (data-lifecycle.md §3). Deterministic, over the shared doubles.
"""

import asyncio

import pytest

from app.application.memory import MemoryNotFoundError, MemoryService
from app.domain.enums import MemoryStatus
from app.domain.erasure import REDACTED
from app.domain.identifiers import MemoryItemId
from tests.support.builders import build_memory_item
from tests.support.doubles import InMemoryMemoryRepository


def _service() -> tuple[MemoryService, InMemoryMemoryRepository]:
    repository = InMemoryMemoryRepository()
    return MemoryService(repository), repository


def test_erase_tombstones_every_version() -> None:
    async def scenario() -> None:
        service, repository = _service()
        await service.create(
            build_memory_item("m1", content="jane.doe phished on host-7")
        )
        await service.update(
            build_memory_item(
                "m1", version=2, content="jane.doe credentials rotated"
            )
        )

        tombstone = await service.erase(MemoryItemId("m1"))

        assert tombstone.status is MemoryStatus.ERASED
        assert tombstone.content == REDACTED
        # Every historical version's text is redacted, not just the latest.
        versions = await repository.list_versions(MemoryItemId("m1"))
        assert [v.version for v in versions] == [1, 2]
        assert all(v.content == REDACTED for v in versions)
        assert all(v.status is MemoryStatus.ERASED for v in versions)

    asyncio.run(scenario())


def test_erase_preserves_structural_correlation() -> None:
    async def scenario() -> None:
        service, _ = _service()
        await service.create(
            build_memory_item(
                "m1",
                type_value="attack_pattern",
                source_investigation_id="inv-9",
                confidence=0.9,
                content="personal knowledge",
            )
        )

        tombstone = await service.erase(MemoryItemId("m1"))

        assert tombstone.id == MemoryItemId("m1")
        assert tombstone.type.value == "attack_pattern"
        assert tombstone.source_investigation_id.value == "inv-9"
        assert tombstone.confidence.value == 0.9

    asyncio.run(scenario())


def test_erase_is_idempotent() -> None:
    async def scenario() -> None:
        service, _ = _service()
        await service.create(build_memory_item("m1", content="secret"))

        first = await service.erase(MemoryItemId("m1"))
        second = await service.erase(MemoryItemId("m1"))

        assert first.status is second.status is MemoryStatus.ERASED
        assert second.content == REDACTED

    asyncio.run(scenario())


def test_erase_unknown_memory_item_raises() -> None:
    async def scenario() -> None:
        service, _ = _service()
        with pytest.raises(MemoryNotFoundError):
            await service.erase(MemoryItemId("missing"))

    asyncio.run(scenario())


def test_erasure_is_distinct_from_deprecation() -> None:
    async def scenario() -> None:
        service, _ = _service()
        await service.create(build_memory_item("m1", content="still here"))

        deprecated = await service.deprecate(MemoryItemId("m1"))

        # Deprecation controls relevance only: the content still exists.
        assert deprecated.status is MemoryStatus.DEPRECATED
        assert deprecated.content == "still here"

        erased = await service.erase(MemoryItemId("m1"))
        assert erased.status is MemoryStatus.ERASED
        assert erased.content == REDACTED

    asyncio.run(scenario())
