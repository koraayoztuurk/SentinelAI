"""Live PostgreSQL tests for the Investigation-family adapters (ES-040).

Opt-in (`pytest -m live`): these tests run against a real PostgreSQL and
verify the exit criteria of ES-040 — deterministic migration from an empty
database, investigation CRUD with every documented lifecycle transition,
evidence/finding/report links, the 0..1 outcome constraint (service- and
database-enforced) and append-ordered, append-only trace reads. Each service
operation runs in its own transaction (`session_scope`), mirroring the
request-scoped unit of work; persistence is always verified through a fresh
session so nothing is read back from a warm identity map.
"""

import asyncio
from datetime import timedelta

import pytest
import sqlalchemy as sa
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from alembic import command
from app.application.investigation import InvestigationService
from app.application.investigation.errors import (
    DuplicateInvestigationError,
    DuplicateOutcomeError,
    EvidenceOwnershipError,
    InvalidLifecycleTransitionError,
)
from app.domain.enums import (
    FindingStatus,
    InvestigationOutcomeStatus,
    InvestigationStatus,
)
from app.domain.identifiers import (
    FindingId,
    InvestigationId,
    InvestigationOutcomeId,
    ReportId,
    TraceEntryId,
)
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import ActorRef, Confidence
from app.infrastructure.persistence.postgres.engine import create_session_factory
from app.infrastructure.persistence.postgres.investigation.repositories import (
    PostgresEvidenceRepository,
    PostgresFindingRepository,
    PostgresInvestigationRepository,
    PostgresOutcomeRepository,
    PostgresReportRepository,
    PostgresTraceRepository,
)
from app.infrastructure.persistence.postgres.session import session_scope
from tests.live.support import (
    alembic_config,
    ensure_schema,
    live_engine,
    truncate_tables,
)
from tests.support.builders import (
    FIXED_TIME,
    build_evidence,
    build_finding,
    build_investigation,
    build_report,
)

pytestmark = pytest.mark.live

_TABLES = (
    "trace_entry",
    "investigation_outcome",
    "report",
    "finding",
    "evidence",
    "investigation",
)


def _service(session: AsyncSession) -> InvestigationService:
    return InvestigationService(
        PostgresInvestigationRepository(session),
        PostgresEvidenceRepository(session),
        PostgresFindingRepository(session),
        PostgresReportRepository(session),
        PostgresOutcomeRepository(session),
        PostgresTraceRepository(session),
    )


async def _reset(engine: AsyncEngine) -> None:
    await truncate_tables(engine, *_TABLES)


# -------------------------------------------------------------------- migration


def test_upgrade_head_from_empty_database_is_deterministic() -> None:
    asyncio.run(_drop_schema())
    command.upgrade(alembic_config(), "head")
    # Re-running against an up-to-date database is a no-op, not an error.
    command.upgrade(alembic_config(), "head")
    asyncio.run(_assert_schema_at_head())


async def _drop_schema() -> None:
    engine = live_engine()
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
    finally:
        await engine.dispose()


async def _assert_schema_at_head() -> None:
    engine = live_engine()
    try:
        async with engine.connect() as connection:
            tables = set(
                await connection.run_sync(
                    lambda sync: sa.inspect(sync).get_table_names()
                )
            )
            version = (
                await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
            ).scalar_one()
    finally:
        await engine.dispose()
    assert set(_TABLES) <= tables
    # The stamped revision is whatever the migration scripts declare as head,
    # so this test stays valid as later migrations extend the chain.
    script_head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    assert version == script_head


# ------------------------------------------------------- investigation lifecycle


def test_investigation_crud_and_full_lifecycle() -> None:
    ensure_schema()
    asyncio.run(_investigation_scenario())


async def _investigation_scenario() -> None:
    engine = live_engine()
    try:
        await _reset(engine)
        factory = create_session_factory(engine)

        investigation = build_investigation(
            "inv-live-1", title="Live persistence", owner="analyst-7"
        )
        async with session_scope(factory) as session:
            await _service(session).create(investigation)

        # Duplicate identifiers are rejected against the persisted state.
        async with session_scope(factory) as session:
            with pytest.raises(DuplicateInvestigationError):
                await _service(session).create(
                    build_investigation("inv-live-1")
                )

        # Round trip through a fresh session preserves every field.
        async with session_scope(factory) as session:
            loaded = await _service(session).get(InvestigationId("inv-live-1"))
        assert loaded.title == "Live persistence"
        assert loaded.owner == ActorRef("analyst-7")
        assert loaded.priority.value == "high"
        assert loaded.status is InvestigationStatus.CREATED
        assert loaded.created_at == FIXED_TIME

        # Every documented transition, one transaction each
        # (spec §10 v1.1.0: suspend/resume, complete, reopen, archive).
        transitions = (
            InvestigationStatus.ACTIVE,
            InvestigationStatus.SUSPENDED,
            InvestigationStatus.ACTIVE,
            InvestigationStatus.COMPLETED,
            InvestigationStatus.ACTIVE,  # reopen
            InvestigationStatus.ARCHIVED,
        )
        for target in transitions:
            async with session_scope(factory) as session:
                await _service(session).change_status(
                    InvestigationId("inv-live-1"), target
                )

        async with session_scope(factory) as session:
            final = await _service(session).get(InvestigationId("inv-live-1"))
        assert final.status is InvestigationStatus.ARCHIVED

        # Archived is terminal — the rejected transition leaves no trace.
        async with session_scope(factory) as session:
            with pytest.raises(InvalidLifecycleTransitionError):
                await _service(session).change_status(
                    InvestigationId("inv-live-1"), InvestigationStatus.ACTIVE
                )
        async with session_scope(factory) as session:
            still = await _service(session).get(InvestigationId("inv-live-1"))
        assert still.status is InvestigationStatus.ARCHIVED
    finally:
        await engine.dispose()


# ------------------------------------------------- evidence / finding / report


def test_evidence_finding_report_links() -> None:
    ensure_schema()
    asyncio.run(_links_scenario())


async def _links_scenario() -> None:
    engine = live_engine()
    try:
        await _reset(engine)
        factory = create_session_factory(engine)

        async with session_scope(factory) as session:
            service = _service(session)
            await service.create(build_investigation("inv-a"))
            await service.create(build_investigation("inv-b"))
            await service.attach_evidence(
                build_evidence(
                    "ev-2", "inv-a", timestamp=FIXED_TIME + timedelta(hours=1)
                )
            )
            await service.attach_evidence(build_evidence("ev-1", "inv-a"))
            await service.attach_evidence(build_evidence("ev-b", "inv-b"))

        # Evidence listing is investigation-scoped and deterministically
        # ordered (timestamp, then id).
        async with session_scope(factory) as session:
            listed = await _service(session).list_evidence(
                InvestigationId("inv-a")
            )
        assert [e.id.value for e in listed] == ["ev-1", "ev-2"]

        # A finding referencing foreign evidence is rejected; nothing persists.
        async with session_scope(factory) as session:
            with pytest.raises(EvidenceOwnershipError):
                await _service(session).create_finding(
                    build_finding(
                        "f-bad", "inv-a", supporting_evidence=("ev-b",)
                    )
                )

        finding = build_finding(
            "f-1",
            "inv-a",
            supporting_evidence=("ev-1", "ev-2"),
            related_entities=("ent-1", "ent-2"),
            related_relationships=("rel-1",),
        )
        async with session_scope(factory) as session:
            await _service(session).create_finding(finding)

        # Array columns round-trip losslessly through a fresh session.
        async with session_scope(factory) as session:
            findings = await _service(session).list_findings(
                InvestigationId("inv-a")
            )
        assert len(findings) == 1
        stored = findings[0]
        assert [e.value for e in stored.supporting_evidence] == ["ev-1", "ev-2"]
        assert [e.value for e in stored.related_entities] == ["ent-1", "ent-2"]
        assert [r.value for r in stored.related_relationships] == ["rel-1"]
        assert stored.status is FindingStatus.PROPOSED

        # Update persists across transactions.
        stored.status = FindingStatus.VALIDATED
        async with session_scope(factory) as session:
            await _service(session).update_finding(stored)
        async with session_scope(factory) as session:
            updated = (
                await _service(session).list_findings(InvestigationId("inv-a"))
            )[0]
        assert updated.status is FindingStatus.VALIDATED

        # Reports link to their investigation and list back.
        async with session_scope(factory) as session:
            await _service(session).create_report(build_report("rep-1", "inv-a"))
        async with session_scope(factory) as session:
            service = _service(session)
            report = await service.get_report(ReportId("rep-1"))
            reports = await service.list_reports(InvestigationId("inv-a"))
        assert report.id == ReportId("rep-1")
        assert [r.id.value for r in reports] == ["rep-1"]
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------- outcome


def test_outcome_is_zero_or_one_per_investigation() -> None:
    ensure_schema()
    asyncio.run(_outcome_scenario())


def _outcome(
    outcome_id: str, investigation_id: str, findings: tuple[str, ...]
) -> InvestigationOutcome:
    return InvestigationOutcome(
        id=InvestigationOutcomeId(outcome_id),
        investigation_id=InvestigationId(investigation_id),
        confidence=Confidence(0.7),
        recommendation="Contain the host.",
        status=InvestigationOutcomeStatus.SYNTHESIZED,
        created_at=FIXED_TIME,
        contributing_findings=tuple(FindingId(f) for f in findings),
        detected_conflicts=("conflicting dns telemetry",),
        open_questions=("initial access vector?",),
    )


async def _outcome_scenario() -> None:
    engine = live_engine()
    try:
        await _reset(engine)
        factory = create_session_factory(engine)

        async with session_scope(factory) as session:
            service = _service(session)
            await service.create(build_investigation("inv-o"))
            await service.attach_evidence(build_evidence("ev-o", "inv-o"))
            await service.create_finding(
                build_finding("f-o", "inv-o", supporting_evidence=("ev-o",))
            )
            await service.create_outcome(_outcome("out-1", "inv-o", ("f-o",)))

        # Round trip preserves the synthesized content.
        async with session_scope(factory) as session:
            stored = await _service(session).get_outcome(
                InvestigationId("inv-o")
            )
        assert stored.recommendation == "Contain the host."
        assert [f.value for f in stored.contributing_findings] == ["f-o"]
        assert stored.detected_conflicts == ("conflicting dns telemetry",)
        assert stored.open_questions == ("initial access vector?",)
        assert stored.report_id is None

        # The service rejects a second outcome (0..1, domain-model §16).
        async with session_scope(factory) as session:
            with pytest.raises(DuplicateOutcomeError):
                await _service(session).create_outcome(
                    _outcome("out-2", "inv-o", ())
                )

        # The database enforces the same rule even below the service.
        raised = False
        try:
            async with session_scope(factory) as session:
                await PostgresOutcomeRepository(session).add(
                    _outcome("out-3", "inv-o", ())
                )
        except IntegrityError:
            raised = True
        assert raised, "unique(investigation_id) did not reject a second outcome"
    finally:
        await engine.dispose()


# ------------------------------------------------------------------------ trace


def test_trace_is_append_only_and_read_in_append_order() -> None:
    ensure_schema()
    asyncio.run(_trace_scenario())


def _entry(entry_id: str, investigation_id: str, summary: str) -> TraceEntry:
    # Identical caller-supplied timestamps on purpose: append order must come
    # from the store, never from the timestamps or the identifier ordering.
    return TraceEntry(
        id=TraceEntryId(entry_id),
        investigation_id=InvestigationId(investigation_id),
        kind=TraceEntryKind.PLANNER_DECISION,
        actor=ActorRef("planner-agent"),
        summary=summary,
        reference="action-1",
        created_at=FIXED_TIME,
    )


async def _trace_scenario() -> None:
    engine = live_engine()
    try:
        await _reset(engine)
        factory = create_session_factory(engine)

        async with session_scope(factory) as session:
            service = _service(session)
            await service.create(build_investigation("inv-t"))
            await service.create(build_investigation("inv-t2"))

        for entry_id, summary in (
            ("t-c", "first"),
            ("t-a", "second"),
            ("t-b", "third"),
        ):
            async with session_scope(factory) as session:
                await _service(session).record_trace(
                    _entry(entry_id, "inv-t", summary)
                )
        async with session_scope(factory) as session:
            await _service(session).record_trace(
                _entry("t-other", "inv-t2", "foreign")
            )

        async with session_scope(factory) as session:
            entries = await _service(session).list_trace(
                InvestigationId("inv-t")
            )
        assert [e.id.value for e in entries] == ["t-c", "t-a", "t-b"]
        assert [e.summary for e in entries] == ["first", "second", "third"]
        assert all(e.created_at == FIXED_TIME for e in entries)

        # The repository port itself is append-only: no update/delete exists.
        assert not hasattr(PostgresTraceRepository, "update")
        assert not hasattr(PostgresTraceRepository, "delete")
    finally:
        await engine.dispose()
