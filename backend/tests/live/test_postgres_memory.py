"""Live PostgreSQL tests for the versioned Memory Item adapter (ES-041).

Opt-in (`pytest -m live`): verifies the ES-041 exit criteria against a real
database — successive ``add`` calls build the version sequence, ``get``
always returns the highest version, deprecation changes only the latest
version's status, and the version history lists back losslessly in ascending
order. Exercised through the Memory Service over the concrete adapter, with
every operation in its own transaction and reads through fresh sessions.
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.application.memory import MemoryService
from app.application.memory.errors import (
    DuplicateMemoryError,
    InvalidMemoryVersionError,
    MemoryNotFoundError,
)
from app.domain.enums import MemoryStatus
from app.domain.identifiers import MemoryItemId
from app.infrastructure.persistence.postgres.engine import create_session_factory
from app.infrastructure.persistence.postgres.memory.repositories import (
    PostgresMemoryRepository,
)
from app.infrastructure.persistence.postgres.session import session_scope
from tests.live.support import ensure_schema, live_engine, truncate_tables
from tests.support.builders import build_memory_item

pytestmark = pytest.mark.live


async def _reset(engine: AsyncEngine) -> None:
    await truncate_tables(engine, "memory_item")


def test_versioned_memory_lifecycle() -> None:
    ensure_schema()
    asyncio.run(_memory_scenario())


def _memory_service(session: AsyncSession) -> MemoryService:
    return MemoryService(PostgresMemoryRepository(session))


async def _memory_scenario() -> None:
    engine = live_engine()
    try:
        await _reset(engine)
        factory = create_session_factory(engine)
        service = _memory_service

        # Version 1 is created; a duplicate id is rejected.
        async with session_scope(factory) as session:
            await service(session).create(
                build_memory_item("mem-1", confidence=0.5)
            )
        async with session_scope(factory) as session:
            with pytest.raises(DuplicateMemoryError):
                await service(session).create(build_memory_item("mem-1"))

        # Supersede appends versions 2 and 3; a version gap is rejected.
        async with session_scope(factory) as session:
            await service(session).update(
                build_memory_item("mem-1", version=2, confidence=0.7)
            )
        async with session_scope(factory) as session:
            with pytest.raises(InvalidMemoryVersionError):
                await service(session).update(
                    build_memory_item("mem-1", version=4)
                )
        async with session_scope(factory) as session:
            await service(session).update(
                build_memory_item(
                    "mem-1",
                    version=3,
                    confidence=0.9,
                    status=MemoryStatus.VERIFIED,
                )
            )

        # `get` returns the latest version through a fresh session.
        async with session_scope(factory) as session:
            latest = await service(session).get(MemoryItemId("mem-1"))
        assert latest.version == 3
        assert latest.confidence.value == 0.9
        assert latest.status is MemoryStatus.VERIFIED

        # Deprecation flips only the latest version's status.
        async with session_scope(factory) as session:
            await service(session).deprecate(MemoryItemId("mem-1"))

        # History lists every version ascending; older rows are untouched.
        async with session_scope(factory) as session:
            history = await service(session).get_history(MemoryItemId("mem-1"))
        assert [item.version for item in history] == [1, 2, 3]
        assert [item.confidence.value for item in history] == [0.5, 0.7, 0.9]
        assert history[0].status is MemoryStatus.CANDIDATE
        assert history[1].status is MemoryStatus.CANDIDATE
        assert history[2].status is MemoryStatus.DEPRECATED

        # Unknown ids stay observable as a business error, not a crash.
        async with session_scope(factory) as session:
            with pytest.raises(MemoryNotFoundError):
                await service(session).get(MemoryItemId("mem-unknown"))
    finally:
        await engine.dispose()
