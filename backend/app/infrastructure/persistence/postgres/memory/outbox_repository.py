"""PostgreSQL outbox repository for the embedding projector (ES-050).

Implements the application-layer :class:`~app.application.memory.OutboxRepository`
read/mark contract over the ``memory_outbox`` table. Bound to one caller-supplied
``AsyncSession`` (the projector opens its own short transaction per cycle, separate
from request sessions). The transactional *write* of new outbox records lives in
the Memory Item persistence adapter (same session as the memory write); this
repository only drains and marks.
"""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.memory import OutboxRecord
from app.infrastructure.persistence.postgres.memory.outbox_orm import (
    MemoryOutboxRow,
)


class PostgresOutboxRepository:
    """``OutboxRepository`` adapter over the ``memory_outbox`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_pending(self, limit: int) -> tuple[OutboxRecord, ...]:
        rows = await self._session.scalars(
            select(MemoryOutboxRow)
            .where(MemoryOutboxRow.status == "pending")
            .order_by(MemoryOutboxRow.seq)
            .limit(limit)
        )
        return tuple(
            OutboxRecord(
                seq=row.seq,
                memory_id=row.memory_id,
                memory_version=row.memory_version,
            )
            for row in rows
        )

    async def mark_processed(self, seq: int) -> None:
        await self._session.execute(
            update(MemoryOutboxRow)
            .where(MemoryOutboxRow.seq == seq)
            .values(status="processed", processed_at=datetime.now(UTC))
        )
        await self._session.flush()

    async def mark_failed(self, seq: int, error: str) -> None:
        await self._session.execute(
            update(MemoryOutboxRow)
            .where(MemoryOutboxRow.seq == seq)
            .values(
                status="failed",
                last_error=error[:500],
                attempts=MemoryOutboxRow.attempts + 1,
            )
        )
        await self._session.flush()
