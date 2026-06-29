"""Unit tests for the Memory Service (ES-007).

Plain pytest functions with a minimal dict-backed in-memory memory repository
double. No live database is required.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.application.memory import (
    DuplicateMemoryError,
    InvalidMemoryVersionError,
    MemoryNotFoundError,
    MemoryService,
)
from app.domain.enums import MemoryStatus
from app.domain.identifiers import InvestigationId, MemoryItemId
from app.domain.memory_item import MemoryItem
from app.domain.value_objects import Confidence, MemoryType

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


# --------------------------------------------------------------- in-memory double


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self._versions: dict[str, list[MemoryItem]] = {}

    async def add(self, memory_item: MemoryItem) -> None:
        self._versions.setdefault(memory_item.id.value, []).append(memory_item)

    async def get(self, memory_id: MemoryItemId) -> MemoryItem | None:
        versions = self._versions.get(memory_id.value)
        if not versions:
            return None
        return max(versions, key=lambda item: item.version)

    async def update(self, memory_item: MemoryItem) -> None:
        versions = self._versions.get(memory_item.id.value, [])
        for index, existing in enumerate(versions):
            if existing.version == memory_item.version:
                versions[index] = memory_item
                return

    async def list_versions(
        self, memory_id: MemoryItemId
    ) -> tuple[MemoryItem, ...]:
        return tuple(self._versions.get(memory_id.value, []))


# ------------------------------------------------------------------------ builders


def _memory_item(
    memory_id: str,
    version: int = 1,
    status: MemoryStatus = MemoryStatus.CANDIDATE,
) -> MemoryItem:
    return MemoryItem(
        id=MemoryItemId(memory_id),
        type=MemoryType("attack_pattern"),
        source_investigation_id=InvestigationId("inv-1"),
        confidence=Confidence(0.9),
        status=status,
        created_at=_NOW,
        version=version,
    )


# --------------------------------------------------------------------------- tests


def test_create_and_get() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        await service.create(_memory_item("m-1"))
        loaded = await service.get(MemoryItemId("m-1"))
        assert loaded.id == MemoryItemId("m-1")
        assert loaded.version == 1

    asyncio.run(scenario())


def test_create_rejects_duplicate() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        await service.create(_memory_item("m-1"))
        with pytest.raises(DuplicateMemoryError):
            await service.create(_memory_item("m-1"))

    asyncio.run(scenario())


def test_create_rejects_non_initial_version() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        with pytest.raises(InvalidMemoryVersionError):
            await service.create(_memory_item("m-1", version=2))

    asyncio.run(scenario())


def test_get_unknown_raises() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        with pytest.raises(MemoryNotFoundError):
            await service.get(MemoryItemId("missing"))

    asyncio.run(scenario())


def test_update_supersedes_and_get_returns_latest() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        await service.create(_memory_item("m-1", version=1))
        await service.update(
            _memory_item("m-1", version=2, status=MemoryStatus.VERIFIED)
        )
        latest = await service.get(MemoryItemId("m-1"))
        assert latest.version == 2
        assert latest.status is MemoryStatus.VERIFIED

    asyncio.run(scenario())


def test_update_rejects_non_sequential_version() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        await service.create(_memory_item("m-1", version=1))
        with pytest.raises(InvalidMemoryVersionError):
            await service.update(_memory_item("m-1", version=3))

    asyncio.run(scenario())


def test_update_unknown_raises() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        with pytest.raises(MemoryNotFoundError):
            await service.update(_memory_item("missing", version=2))

    asyncio.run(scenario())


def test_get_history_is_ascending_and_preserves_versions() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        await service.create(_memory_item("m-1", version=1))
        await service.update(
            _memory_item("m-1", version=2, status=MemoryStatus.VERIFIED)
        )
        await service.update(
            _memory_item("m-1", version=3, status=MemoryStatus.ORGANIZATIONAL)
        )
        history = await service.get_history(MemoryItemId("m-1"))
        assert [item.version for item in history] == [1, 2, 3]
        # Earlier versions remain immutable.
        assert history[0].status is MemoryStatus.CANDIDATE
        assert history[1].status is MemoryStatus.VERIFIED

    asyncio.run(scenario())


def test_deprecate_changes_only_status_of_latest() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        await service.create(_memory_item("m-1", version=1))
        await service.update(
            _memory_item("m-1", version=2, status=MemoryStatus.VERIFIED)
        )
        deprecated = await service.deprecate(MemoryItemId("m-1"))
        assert deprecated.status is MemoryStatus.DEPRECATED
        assert deprecated.version == 2

        history = await service.get_history(MemoryItemId("m-1"))
        # The superseded version 1 is untouched.
        assert history[0].version == 1
        assert history[0].status is MemoryStatus.CANDIDATE

    asyncio.run(scenario())


def test_deprecate_unknown_raises() -> None:
    async def scenario() -> None:
        service = MemoryService(InMemoryMemoryRepository())
        with pytest.raises(MemoryNotFoundError):
            await service.deprecate(MemoryItemId("missing"))

    asyncio.run(scenario())
