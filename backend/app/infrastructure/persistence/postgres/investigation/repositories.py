"""PostgreSQL repository adapters for the Investigation family (ES-040).

Concrete implementations of the Investigation Service's repository ports
(:mod:`app.application.investigation.repositories`). Each adapter is bound to
one caller-supplied :class:`~sqlalchemy.ext.asyncio.AsyncSession`; the whole
adapter set of a request shares that session, so a service operation runs as
one local transaction whose boundary (commit/rollback) is owned by the caller
(the request-scoped session, ES-042). Adapters flush after every write so
database constraint violations surface inside the owning operation.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import EvidenceId, FindingId, InvestigationId, ReportId
from app.domain.investigation import Investigation
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.report import Report
from app.domain.trace import TraceEntry
from app.infrastructure.persistence.postgres.investigation.mappers import (
    evidence_to_domain,
    evidence_to_row,
    finding_to_domain,
    finding_to_row,
    investigation_to_domain,
    investigation_to_row,
    outcome_to_domain,
    outcome_to_row,
    report_to_domain,
    report_to_row,
    trace_entry_to_domain,
    trace_entry_to_row,
)
from app.infrastructure.persistence.postgres.investigation.orm import (
    EvidenceRow,
    FindingRow,
    InvestigationOutcomeRow,
    InvestigationRow,
    ReportRow,
    TraceEntryRow,
)


class PostgresInvestigationRepository:
    """``InvestigationRepository`` adapter over the ``investigation`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, investigation: Investigation) -> None:
        self._session.add(investigation_to_row(investigation))
        await self._session.flush()

    async def get(
        self, investigation_id: InvestigationId
    ) -> Investigation | None:
        row = await self._session.get(InvestigationRow, investigation_id.value)
        return None if row is None else investigation_to_domain(row)

    async def update(self, investigation: Investigation) -> None:
        await self._session.merge(investigation_to_row(investigation))
        await self._session.flush()


class PostgresEvidenceRepository:
    """``EvidenceRepository`` adapter over the ``evidence`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, evidence: Evidence) -> None:
        self._session.add(evidence_to_row(evidence))
        await self._session.flush()

    async def get(self, evidence_id: EvidenceId) -> Evidence | None:
        row = await self._session.get(EvidenceRow, evidence_id.value)
        return None if row is None else evidence_to_domain(row)

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Evidence, ...]:
        rows = await self._session.scalars(
            select(EvidenceRow)
            .where(EvidenceRow.investigation_id == investigation_id.value)
            .order_by(EvidenceRow.timestamp, EvidenceRow.id)
        )
        return tuple(evidence_to_domain(row) for row in rows)


class PostgresFindingRepository:
    """``FindingRepository`` adapter over the ``finding`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, finding: Finding) -> None:
        self._session.add(finding_to_row(finding))
        await self._session.flush()

    async def get(self, finding_id: FindingId) -> Finding | None:
        row = await self._session.get(FindingRow, finding_id.value)
        return None if row is None else finding_to_domain(row)

    async def update(self, finding: Finding) -> None:
        await self._session.merge(finding_to_row(finding))
        await self._session.flush()

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Finding, ...]:
        rows = await self._session.scalars(
            select(FindingRow)
            .where(FindingRow.investigation_id == investigation_id.value)
            .order_by(FindingRow.created_at, FindingRow.id)
        )
        return tuple(finding_to_domain(row) for row in rows)


class PostgresReportRepository:
    """``ReportRepository`` adapter over the ``report`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, report: Report) -> None:
        self._session.add(report_to_row(report))
        await self._session.flush()

    async def get(self, report_id: ReportId) -> Report | None:
        row = await self._session.get(ReportRow, report_id.value)
        return None if row is None else report_to_domain(row)

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Report, ...]:
        rows = await self._session.scalars(
            select(ReportRow)
            .where(ReportRow.investigation_id == investigation_id.value)
            .order_by(ReportRow.created_at, ReportRow.id)
        )
        return tuple(report_to_domain(row) for row in rows)


class PostgresOutcomeRepository:
    """``OutcomeRepository`` adapter over the ``investigation_outcome`` table.

    The table's unique ``investigation_id`` enforces the 0..1 rule at the
    database level in addition to the service's pre-check.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, outcome: InvestigationOutcome) -> None:
        self._session.add(outcome_to_row(outcome))
        await self._session.flush()

    async def get_for_investigation(
        self, investigation_id: InvestigationId
    ) -> InvestigationOutcome | None:
        row = (
            await self._session.scalars(
                select(InvestigationOutcomeRow).where(
                    InvestigationOutcomeRow.investigation_id
                    == investigation_id.value
                )
            )
        ).one_or_none()
        return None if row is None else outcome_to_domain(row)


class PostgresTraceRepository:
    """``TraceRepository`` adapter over the append-only ``trace_entry`` table.

    Append order is materialized by the server-generated ``seq`` column;
    ``list_for_investigation`` orders by it, never by the caller-supplied
    timestamps.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: TraceEntry) -> None:
        self._session.add(trace_entry_to_row(entry))
        await self._session.flush()

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[TraceEntry, ...]:
        rows = await self._session.scalars(
            select(TraceEntryRow)
            .where(TraceEntryRow.investigation_id == investigation_id.value)
            .order_by(TraceEntryRow.seq)
        )
        return tuple(trace_entry_to_domain(row) for row in rows)
