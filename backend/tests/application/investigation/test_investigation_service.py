"""Unit tests for the Investigation Service (ES-005).

Plain pytest functions with minimal dict-backed in-memory repository doubles.
No live database is required.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.application.investigation import (
    DuplicateEvidenceError,
    DuplicateInvestigationError,
    EvidenceNotFoundError,
    EvidenceOwnershipError,
    InvalidLifecycleTransitionError,
    InvestigationNotFoundError,
    InvestigationService,
    InvestigationValidationError,
    ReportNotFoundError,
)
from app.domain.enums import FindingStatus, InvestigationStatus
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import EvidenceId, FindingId, InvestigationId, ReportId
from app.domain.investigation import Investigation
from app.domain.report import Report
from app.domain.value_objects import (
    ActorRef,
    Confidence,
    EvidenceIntegrity,
    EvidenceSource,
    Priority,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


# --------------------------------------------------------------- in-memory doubles


class InMemoryInvestigationRepository:
    def __init__(self) -> None:
        self._items: dict[str, Investigation] = {}

    async def add(self, investigation: Investigation) -> None:
        self._items[investigation.id.value] = investigation

    async def get(self, investigation_id: InvestigationId) -> Investigation | None:
        return self._items.get(investigation_id.value)

    async def update(self, investigation: Investigation) -> None:
        self._items[investigation.id.value] = investigation


class InMemoryEvidenceRepository:
    def __init__(self) -> None:
        self._items: dict[str, Evidence] = {}

    async def add(self, evidence: Evidence) -> None:
        self._items[evidence.id.value] = evidence

    async def get(self, evidence_id: EvidenceId) -> Evidence | None:
        return self._items.get(evidence_id.value)

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Evidence, ...]:
        return tuple(
            e
            for e in self._items.values()
            if e.investigation_id == investigation_id
        )


class InMemoryFindingRepository:
    def __init__(self) -> None:
        self._items: dict[str, Finding] = {}

    async def add(self, finding: Finding) -> None:
        self._items[finding.id.value] = finding

    async def get(self, finding_id: FindingId) -> Finding | None:
        return self._items.get(finding_id.value)

    async def update(self, finding: Finding) -> None:
        self._items[finding.id.value] = finding

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Finding, ...]:
        return tuple(
            f
            for f in self._items.values()
            if f.investigation_id == investigation_id
        )


class InMemoryReportRepository:
    def __init__(self) -> None:
        self._items: dict[str, Report] = {}

    async def add(self, report: Report) -> None:
        self._items[report.id.value] = report

    async def get(self, report_id: ReportId) -> Report | None:
        return self._items.get(report_id.value)

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Report, ...]:
        return tuple(
            r
            for r in self._items.values()
            if r.investigation_id == investigation_id
        )


# ------------------------------------------------------------------------ builders


def _make_service() -> InvestigationService:
    return InvestigationService(
        InMemoryInvestigationRepository(),
        InMemoryEvidenceRepository(),
        InMemoryFindingRepository(),
        InMemoryReportRepository(),
    )


def _investigation(
    investigation_id: str,
    status: InvestigationStatus = InvestigationStatus.CREATED,
) -> Investigation:
    return Investigation(
        id=InvestigationId(investigation_id),
        title="Test investigation",
        status=status,
        created_at=_NOW,
        owner=ActorRef("analyst-1"),
        priority=Priority("high"),
    )


def _evidence(evidence_id: str, investigation_id: str) -> Evidence:
    return Evidence(
        id=EvidenceId(evidence_id),
        investigation_id=InvestigationId(investigation_id),
        source=EvidenceSource("siem"),
        timestamp=_NOW,
        integrity=EvidenceIntegrity("token"),
        content="raw",
    )


def _finding(
    finding_id: str, investigation_id: str, evidence_ids: tuple[str, ...]
) -> Finding:
    return Finding(
        id=FindingId(finding_id),
        investigation_id=InvestigationId(investigation_id),
        supporting_evidence=tuple(EvidenceId(e) for e in evidence_ids),
        creator=ActorRef("analyst-1"),
        created_at=_NOW,
        confidence=Confidence(0.8),
        status=FindingStatus.PROPOSED,
    )


def _report(report_id: str, investigation_id: str) -> Report:
    return Report(
        id=ReportId(report_id),
        investigation_id=InvestigationId(investigation_id),
        author=ActorRef("analyst-1"),
        created_at=_NOW,
    )


# ----------------------------------------------------------------- investigation


def test_create_and_get() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        loaded = await service.get(InvestigationId("inv-1"))
        assert loaded.id == InvestigationId("inv-1")

    asyncio.run(scenario())


def test_create_rejects_duplicate() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        with pytest.raises(DuplicateInvestigationError):
            await service.create(_investigation("inv-1"))

    asyncio.run(scenario())


def test_create_rejects_blank_title() -> None:
    async def scenario() -> None:
        service = _make_service()
        investigation = Investigation(
            id=InvestigationId("inv-1"),
            title="   ",
            status=InvestigationStatus.CREATED,
            created_at=_NOW,
            owner=ActorRef("analyst-1"),
            priority=Priority("high"),
        )
        with pytest.raises(InvestigationValidationError):
            await service.create(investigation)

    asyncio.run(scenario())


def test_create_rejects_non_created_status() -> None:
    async def scenario() -> None:
        service = _make_service()
        with pytest.raises(InvestigationValidationError):
            await service.create(
                _investigation("inv-1", InvestigationStatus.ACTIVE)
            )

    asyncio.run(scenario())


def test_get_unknown_raises() -> None:
    async def scenario() -> None:
        service = _make_service()
        with pytest.raises(InvestigationNotFoundError):
            await service.get(InvestigationId("missing"))

    asyncio.run(scenario())


def test_valid_lifecycle_transition() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        updated = await service.change_status(
            InvestigationId("inv-1"), InvestigationStatus.ACTIVE
        )
        assert updated.status is InvestigationStatus.ACTIVE

    asyncio.run(scenario())


def test_invalid_lifecycle_transition() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        with pytest.raises(InvalidLifecycleTransitionError):
            await service.change_status(
                InvestigationId("inv-1"), InvestigationStatus.COMPLETED
            )

    asyncio.run(scenario())


def test_change_status_only_modifies_status() -> None:
    async def scenario() -> None:
        service = _make_service()
        original = _investigation("inv-1")
        await service.create(original)
        updated = await service.change_status(
            InvestigationId("inv-1"), InvestigationStatus.ACTIVE
        )
        assert updated.status is InvestigationStatus.ACTIVE
        assert updated.title == original.title
        assert updated.created_at == original.created_at
        assert updated.owner == original.owner
        assert updated.priority == original.priority

    asyncio.run(scenario())


# ----------------------------------------------------------------------- evidence


def test_attach_evidence_and_list() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        await service.attach_evidence(_evidence("ev-1", "inv-1"))
        listed = await service.list_evidence(InvestigationId("inv-1"))
        assert len(listed) == 1
        assert listed[0].id == EvidenceId("ev-1")

    asyncio.run(scenario())


def test_attach_evidence_duplicate() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        await service.attach_evidence(_evidence("ev-1", "inv-1"))
        with pytest.raises(DuplicateEvidenceError):
            await service.attach_evidence(_evidence("ev-1", "inv-1"))

    asyncio.run(scenario())


def test_attach_evidence_unknown_investigation() -> None:
    async def scenario() -> None:
        service = _make_service()
        with pytest.raises(InvestigationNotFoundError):
            await service.attach_evidence(_evidence("ev-1", "missing"))

    asyncio.run(scenario())


# ------------------------------------------------------------------------ finding


def test_create_finding_success() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        await service.attach_evidence(_evidence("ev-1", "inv-1"))
        finding = await service.create_finding(_finding("f-1", "inv-1", ("ev-1",)))
        assert finding.id == FindingId("f-1")
        listed = await service.list_findings(InvestigationId("inv-1"))
        assert len(listed) == 1

    asyncio.run(scenario())


def test_create_finding_unknown_evidence() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        with pytest.raises(EvidenceNotFoundError):
            await service.create_finding(_finding("f-1", "inv-1", ("ev-x",)))

    asyncio.run(scenario())


def test_create_finding_foreign_evidence() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        await service.create(_investigation("inv-2"))
        await service.attach_evidence(_evidence("ev-1", "inv-2"))
        with pytest.raises(EvidenceOwnershipError):
            await service.create_finding(_finding("f-1", "inv-1", ("ev-1",)))

    asyncio.run(scenario())


# ------------------------------------------------------------------------- report


def test_create_report_and_list() -> None:
    async def scenario() -> None:
        service = _make_service()
        await service.create(_investigation("inv-1"))
        await service.create_report(_report("rep-1", "inv-1"))
        listed = await service.list_reports(InvestigationId("inv-1"))
        assert len(listed) == 1

    asyncio.run(scenario())


def test_create_report_unknown_investigation() -> None:
    async def scenario() -> None:
        service = _make_service()
        with pytest.raises(InvestigationNotFoundError):
            await service.create_report(_report("rep-1", "missing"))

    asyncio.run(scenario())


def test_get_report_unknown_raises() -> None:
    async def scenario() -> None:
        service = _make_service()
        with pytest.raises(ReportNotFoundError):
            await service.get_report(ReportId("missing"))

    asyncio.run(scenario())
