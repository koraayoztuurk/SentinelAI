"""PostgreSQL repository adapter for the versioned Memory Item (ES-041, ES-050).

Concrete implementation of the Memory Service's repository port
(:mod:`app.application.memory.repositories`) with the version semantics the
port documents: ``add`` inserts a new version row, ``get`` returns the latest
version, ``list_versions`` returns every version ascending, and ``update``
modifies the matching version in place (used only for the latest-version
status change in deprecation). Session/transaction ownership follows the
Investigation-family adapters: one caller-supplied session per request.

Transactional outbox (ES-050, ADR-012): every new Memory Item version (``add``
— used by both create and version-supersede) records a ``memory_outbox`` intent
**in the same session/transaction**, so the authoritative write and the intent
to derive an embedding commit atomically (no request path writes to two stores —
AC-14). Deprecation goes through ``update`` (in-place status change), which
writes no outbox record: the embeddable text is unchanged, so no re-embed is
owed.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.identifiers import MemoryItemId
from app.domain.memory_item import MemoryItem
from app.infrastructure.persistence.postgres.memory.mappers import (
    memory_item_to_domain,
    memory_item_to_row,
)
from app.infrastructure.persistence.postgres.memory.orm import MemoryItemRow
from app.infrastructure.persistence.postgres.memory.outbox_orm import (
    MemoryOutboxRow,
)


class PostgresMemoryRepository:
    """``MemoryRepository`` adapter over the ``memory_item`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, memory_item: MemoryItem) -> None:
        self._session.add(memory_item_to_row(memory_item))
        # Same-transaction derivation intent (ADR-012 outbox).
        self._session.add(
            MemoryOutboxRow(
                memory_id=memory_item.id.value,
                memory_version=memory_item.version,
            )
        )
        await self._session.flush()

    async def get(self, memory_id: MemoryItemId) -> MemoryItem | None:
        row = (
            await self._session.scalars(
                select(MemoryItemRow)
                .where(MemoryItemRow.id == memory_id.value)
                .order_by(MemoryItemRow.version.desc())
                .limit(1)
            )
        ).one_or_none()
        return None if row is None else memory_item_to_domain(row)

    async def update(self, memory_item: MemoryItem) -> None:
        await self._session.merge(memory_item_to_row(memory_item))
        await self._session.flush()

    async def list_versions(
        self, memory_id: MemoryItemId
    ) -> tuple[MemoryItem, ...]:
        rows = await self._session.scalars(
            select(MemoryItemRow)
            .where(MemoryItemRow.id == memory_id.value)
            .order_by(MemoryItemRow.version)
        )
        return tuple(memory_item_to_domain(row) for row in rows)
