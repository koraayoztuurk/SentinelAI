"""Durable audit recorder (PostgreSQL, ES-069 / ADR-018).

The concrete sink behind the application-layer ``AuditRecorder`` port (ES-021).
The port is unchanged — this is a new adapter, not a new contract — so swapping
the log-only recorder for a durable one is a composition-root decision.

Three properties are worth reading the code for:

**Its own transaction.** Each record is written in a session of its own, never
joined to the transaction of the activity it describes (ADR-018 §9). Audit
observes the platform; it must not be able to fail it. The cost — an activity
and its record are not atomic — is accepted deliberately.

**Serialized appends.** A single global chain (§3) means two concurrent appends
must not both read the same head. A transaction-scoped advisory lock serializes
them; it is taken before the head is read and released when the transaction
ends. A ``SELECT … FOR UPDATE`` on the head would not do: it locks nothing when
the table is empty, so the very first two records could race.

**Expiry never edits.** Retention removes whole records from the oldest end
(§5); no retained record is ever modified, which is what keeps the chain
meaningful.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.audit.events import AuditEvent
from app.infrastructure.persistence.postgres.audit.chain import (
    GENESIS_HASH,
    ChainVerification,
    SealedAuditRecord,
    compute_hash,
    verify_chain,
)
from app.infrastructure.persistence.postgres.audit.orm import AuditRecordRow

logger = logging.getLogger(__name__)

# Advisory-lock key for the audit chain head. Arbitrary but fixed: it only has
# to be distinct from any other advisory lock the application takes.
_CHAIN_LOCK_KEY = 8_069_001


class PostgresAuditRecorder:
    """``AuditRecorder`` adapter over the append-only ``audit_log`` table."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        # The adapter owns the clock (the no-clock rule constrains the domain
        # and services, not adapters) because the timestamp is part of the
        # sealed content and must exist before the digest is computed.
        self._clock = clock

    async def record(self, event: AuditEvent) -> None:
        """Append one sealed audit record."""

        recorded_at = self._clock()
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"),
                    {"key": _CHAIN_LOCK_KEY},
                )
                head = await session.scalar(
                    select(AuditRecordRow.record_hash)
                    .order_by(AuditRecordRow.seq.desc())
                    .limit(1)
                )
                previous_hash = head or GENESIS_HASH
                row = AuditRecordRow(
                    action=event.action.value,
                    outcome=event.outcome.value,
                    subject=event.subject,
                    identity_kind=event.identity_kind,
                    operation=event.operation,
                    resource=event.resource,
                    request_id=event.request_id,
                    recorded_at=recorded_at,
                    previous_hash=previous_hash,
                    record_hash="",
                )
                session.add(row)
                # The digest covers ``seq``, so the identity has to exist
                # before the record can be sealed.
                await session.flush()
                row.record_hash = compute_hash(
                    seq=row.seq,
                    action=row.action,
                    outcome=row.outcome,
                    subject=row.subject,
                    identity_kind=row.identity_kind,
                    operation=row.operation,
                    resource=row.resource,
                    request_id=row.request_id,
                    recorded_at=recorded_at,
                    previous_hash=previous_hash,
                )

    async def verify(self, limit: int | None = None) -> ChainVerification:
        """Verify the retained record sequence (ADR-018 §3).

        ``limit`` verifies only the most recent records — the chain is
        append-only, so a bounded suffix is a meaningful check on a large log
        (a full pass becomes a periodic job, ADR-018 Consequences).
        """

        async with self._session_factory() as session:
            if limit is None:
                rows = list(
                    await session.scalars(
                        select(AuditRecordRow).order_by(AuditRecordRow.seq)
                    )
                )
            else:
                newest = await session.scalars(
                    select(AuditRecordRow)
                    .order_by(AuditRecordRow.seq.desc())
                    .limit(limit)
                )
                rows = list(reversed(list(newest)))
        return verify_chain(tuple(_to_record(row) for row in rows))

    async def expire(self, older_than: datetime) -> int:
        """Remove whole records recorded before ``older_than``; never edit one.

        Returns how many were removed. The remaining earliest record's
        predecessor link becomes unverifiable, which chain verification treats
        as the retention boundary rather than as tampering.
        """

        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    delete(AuditRecordRow).where(
                        AuditRecordRow.recorded_at < older_than
                    )
                )
                removed = int(getattr(result, "rowcount", 0) or 0)
        return removed


def _to_record(row: AuditRecordRow) -> SealedAuditRecord:
    return SealedAuditRecord(
        seq=row.seq,
        action=row.action,
        outcome=row.outcome,
        subject=row.subject,
        identity_kind=row.identity_kind,
        operation=row.operation,
        resource=row.resource,
        request_id=row.request_id,
        recorded_at=row.recorded_at,
        previous_hash=row.previous_hash,
        record_hash=row.record_hash,
    )
