"""Live PostgreSQL tests for the durable audit sink (ES-069, ADR-018).

Opt-in (`pytest -m live`). The chain arithmetic is verified without a database
(`tests/infrastructure/test_audit_chain.py`); what needs a real store is
everything the adapter does *around* it — that appends land in order and link
to each other, that verification reads what was actually written, that
retention removes whole records and leaves a chain that still verifies, and
that the audit write is a transaction of its own.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.application.audit import AuditAction, AuditEvent, AuditOutcome
from app.infrastructure.persistence.postgres.audit import (
    GENESIS_HASH,
    PostgresAuditRecorder,
)
from app.infrastructure.persistence.postgres.engine import create_session_factory
from tests.live.support import ensure_schema, live_engine, truncate_tables

pytestmark = pytest.mark.live

_T0 = datetime(2026, 7, 26, 9, 0, tzinfo=UTC)


def _event(
    request_id: str,
    *,
    action: AuditAction = AuditAction.OPERATION_PERFORMED,
    subject: str | None = "analyst",
    resource: str | None = "inv-1",
) -> AuditEvent:
    return AuditEvent(
        action=action,
        outcome=AuditOutcome.SUCCEEDED,
        subject=subject,
        identity_kind="human",
        operation="GET /api/v1/investigations/inv-1",
        request_id=request_id,
        resource=resource,
    )


class _Clock:
    """A hand-advanced clock, so retention windows need no waiting."""

    def __init__(self, now: datetime = _T0) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


async def _reset(engine: AsyncEngine) -> None:
    await truncate_tables(engine, "audit_log")


def test_appended_records_form_a_verifiable_chain() -> None:
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            recorder = PostgresAuditRecorder(create_session_factory(engine))

            for index in range(5):
                await recorder.record(_event(f"req-{index}"))

            result = await recorder.verify()
            assert result.valid, result.reason
            assert result.checked == 5
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_the_first_record_links_to_the_genesis_hash() -> None:
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            recorder = PostgresAuditRecorder(create_session_factory(engine))

            await recorder.record(_event("req-0"))

            async with engine.connect() as connection:
                previous = await connection.scalar(
                    text("SELECT previous_hash FROM audit_log ORDER BY seq LIMIT 1")
                )
            assert previous == GENESIS_HASH
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_tampering_with_a_stored_record_is_detected() -> None:
    # The guarantee stated in ADR-018 §3, exercised where it matters: an UPDATE
    # straight against the table, which is exactly what an attacker with
    # database access would do.
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            recorder = PostgresAuditRecorder(create_session_factory(engine))
            for index in range(3):
                await recorder.record(_event(f"req-{index}"))

            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE audit_log SET subject = 'someone-else' "
                        "WHERE seq = (SELECT MIN(seq) + 1 FROM audit_log)"
                    )
                )

            result = await recorder.verify()
            assert not result.valid
            assert result.reason is not None
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_deleting_a_record_from_the_middle_is_detected() -> None:
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            recorder = PostgresAuditRecorder(create_session_factory(engine))
            for index in range(4):
                await recorder.record(_event(f"req-{index}"))

            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "DELETE FROM audit_log "
                        "WHERE seq = (SELECT MIN(seq) + 1 FROM audit_log)"
                    )
                )

            assert not (await recorder.verify()).valid
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_retention_removes_whole_records_and_leaves_a_valid_chain() -> None:
    # Expiry is the *only* sanctioned removal (ADR-018 §5): it takes whole
    # records from the oldest end, and what remains must still verify — the
    # truncated head is a retention boundary, not tampering.
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            clock = _Clock()
            recorder = PostgresAuditRecorder(
                create_session_factory(engine), clock=clock
            )
            for index in range(3):
                await recorder.record(_event(f"old-{index}"))
            clock.advance(timedelta(days=400))
            for index in range(2):
                await recorder.record(_event(f"new-{index}"))

            removed = await recorder.expire(_T0 + timedelta(days=365))

            assert removed == 3
            result = await recorder.verify()
            assert result.valid, result.reason
            assert result.checked == 2
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_expiry_never_edits_a_retained_record() -> None:
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            clock = _Clock()
            recorder = PostgresAuditRecorder(
                create_session_factory(engine), clock=clock
            )
            await recorder.record(_event("old-0"))
            clock.advance(timedelta(days=400))
            await recorder.record(_event("kept-0"))

            async with engine.connect() as connection:
                before = await connection.scalar(
                    text(
                        "SELECT record_hash FROM audit_log "
                        "ORDER BY seq DESC LIMIT 1"
                    )
                )
            await recorder.expire(_T0 + timedelta(days=365))
            async with engine.connect() as connection:
                after = await connection.scalar(
                    text(
                        "SELECT record_hash FROM audit_log "
                        "ORDER BY seq DESC LIMIT 1"
                    )
                )

            assert before == after
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_concurrent_appends_do_not_fork_the_chain() -> None:
    # A single global chain (ADR-018 §3) means two appends must not read the
    # same head. Without the advisory lock this is exactly where the chain
    # would silently fork.
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            recorder = PostgresAuditRecorder(create_session_factory(engine))

            await asyncio.gather(
                *(recorder.record(_event(f"req-{index}")) for index in range(8))
            )

            result = await recorder.verify()
            assert result.valid, result.reason
            assert result.checked == 8
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_the_audit_write_is_its_own_transaction() -> None:
    # ADR-018 §9 / AC-14: the record must not depend on a caller's transaction,
    # so a caller rolling back leaves the audit record standing.
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            session_factory = create_session_factory(engine)
            recorder = PostgresAuditRecorder(session_factory)

            async with session_factory() as caller_session:
                async with caller_session.begin():
                    await caller_session.execute(text("SELECT 1"))
                    await recorder.record(_event("req-0"))
                    await caller_session.rollback()

            async with engine.connect() as connection:
                count = await connection.scalar(
                    text("SELECT COUNT(*) FROM audit_log")
                )
            assert count == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_a_bounded_verification_checks_the_newest_records() -> None:
    # A full pass becomes a periodic job at volume (ADR-018 Consequences), so a
    # bounded suffix has to be meaningful on its own: the oldest record it
    # covers is a boundary, exactly like the retention boundary.
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            recorder = PostgresAuditRecorder(create_session_factory(engine))
            for index in range(6):
                await recorder.record(_event(f"req-{index}"))

            result = await recorder.verify(limit=2)

            assert result.valid, result.reason
            assert result.checked == 2
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_a_bounded_verification_still_detects_tampering_in_range() -> None:
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            recorder = PostgresAuditRecorder(create_session_factory(engine))
            for index in range(6):
                await recorder.record(_event(f"req-{index}"))

            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE audit_log SET subject = 'someone-else' "
                        "WHERE seq = (SELECT MAX(seq) FROM audit_log)"
                    )
                )

            assert not (await recorder.verify(limit=2)).valid
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_the_erasure_action_is_stored_as_recorded() -> None:
    ensure_schema()

    async def scenario() -> None:
        engine = live_engine()
        try:
            await _reset(engine)
            recorder = PostgresAuditRecorder(create_session_factory(engine))

            await recorder.record(
                _event(
                    "req-0",
                    action=AuditAction.INVESTIGATION_ERASED,
                    resource="inv-erased",
                )
            )

            async with engine.connect() as connection:
                row = (
                    await connection.execute(
                        text(
                            "SELECT action, resource FROM audit_log "
                            "ORDER BY seq DESC LIMIT 1"
                        )
                    )
                ).one()
            assert row.action == "investigation.erased"
            assert row.resource == "inv-erased"
        finally:
            await engine.dispose()

    asyncio.run(scenario())
