"""PostgreSQL outbox repository for the embedding projector (ES-050/ES-067).

Implements the application-layer :class:`~app.application.memory.OutboxRepository`
read/mark contract over the ``memory_outbox`` table. Bound to one caller-supplied
``AsyncSession`` (the projector opens its own short transaction per cycle, separate
from request sessions). The transactional *write* of new outbox records lives in
the Memory Item persistence adapter (same session as the memory write); this
repository only drains and marks.

Retry scheduling (ES-067) is applied here because this adapter owns the clock:
the projector decides *how long* to wait, the store decides *when* that is.
``next_attempt_at`` is both **written and compared** on the database clock, so
due-ness never depends on the application host's clock agreeing with the
database's — routine skew between a container and its host would otherwise
shift every deadline. It also means a multi-instance deployment agrees on
due-ness for free (leader election for the runner itself stays post-release).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.memory import OutboxRecord
from app.infrastructure.persistence.postgres.memory.outbox_orm import (
    MemoryOutboxRow,
)

# Bound on the provider error text retained for operators.
_ERROR_LIMIT = 500


class PostgresOutboxRepository:
    """``OutboxRepository`` adapter over the ``memory_outbox`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_due(self, limit: int) -> tuple[OutboxRecord, ...]:
        rows = await self._session.scalars(
            select(MemoryOutboxRow)
            .where(
                MemoryOutboxRow.status == "pending",
                # A fresh record has no next-attempt time; a rescheduled one is
                # due once its backoff has elapsed on the database clock.
                or_(
                    MemoryOutboxRow.next_attempt_at.is_(None),
                    MemoryOutboxRow.next_attempt_at <= func.now(),
                ),
            )
            .order_by(MemoryOutboxRow.seq)
            .limit(limit)
        )
        return tuple(
            OutboxRecord(
                seq=row.seq,
                memory_id=row.memory_id,
                memory_version=row.memory_version,
                attempts=row.attempts,
            )
            for row in rows
        )

    async def mark_processed(self, seq: int) -> None:
        await self._session.execute(
            update(MemoryOutboxRow)
            .where(MemoryOutboxRow.seq == seq)
            .values(
                status="processed",
                processed_at=datetime.now(UTC),
                next_attempt_at=None,
            )
        )
        await self._session.flush()

    async def mark_retry(
        self, seq: int, error: str, delay_seconds: float
    ) -> None:
        await self._session.execute(
            update(MemoryOutboxRow)
            .where(MemoryOutboxRow.seq == seq)
            .values(
                # Stays pending — the backoff, not the status, holds it back.
                status="pending",
                last_error=error[:_ERROR_LIMIT],
                attempts=MemoryOutboxRow.attempts + 1,
                # Deadline set on the **database** clock, because ``list_due``
                # compares against it. Setting it from the application clock
                # would mix two clocks: any skew between the app host and the
                # database (routine with containers) would shift due-ness in
                # either direction.
                next_attempt_at=func.now() + timedelta(seconds=delay_seconds),
            )
        )
        await self._session.flush()

    async def mark_dead_letter(self, seq: int, error: str) -> None:
        await self._session.execute(
            update(MemoryOutboxRow)
            .where(MemoryOutboxRow.seq == seq)
            .values(
                status="dead_letter",
                last_error=error[:_ERROR_LIMIT],
                attempts=MemoryOutboxRow.attempts + 1,
                next_attempt_at=None,
            )
        )
        await self._session.flush()

    async def count_dead_letters(self) -> int:
        """How many records are retired unprojected (operational visibility)."""

        result = await self._session.scalar(
            select(func.count())
            .select_from(MemoryOutboxRow)
            .where(MemoryOutboxRow.status == "dead_letter")
        )
        return int(result or 0)
