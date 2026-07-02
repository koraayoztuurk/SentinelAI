"""Shared in-memory test doubles (Test Foundation, ES-032).

Reusable, dict-backed repository doubles for the Investigation family plus
deterministic id/clock doubles, matching the repository/generation ports the
services and API depend on. They are plain classes (no pytest fixtures), so any
test can construct and wire them directly. This is common validation
infrastructure, not owned by a single domain.
"""

from datetime import datetime

from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import (
    EvidenceId,
    FindingId,
    InvestigationId,
    ReportId,
)
from app.domain.investigation import Investigation
from app.domain.report import Report

# ------------------------------------------------------------- repository doubles


class InMemoryInvestigationRepository:
    """Dict-backed Investigation repository double."""

    def __init__(self) -> None:
        self._items: dict[str, Investigation] = {}

    async def add(self, investigation: Investigation) -> None:
        self._items[investigation.id.value] = investigation

    async def get(self, investigation_id: InvestigationId) -> Investigation | None:
        return self._items.get(investigation_id.value)

    async def update(self, investigation: Investigation) -> None:
        self._items[investigation.id.value] = investigation


class InMemoryEvidenceRepository:
    """Dict-backed Evidence repository double."""

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
    """Dict-backed Finding repository double."""

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
    """Dict-backed Report repository double."""

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


# ------------------------------------------------------------ generation doubles


class SequentialIdGenerator:
    """Deterministic ``IdGenerator``: emits ``<prefix>-1``, ``<prefix>-2``, ..."""

    def __init__(self, prefix: str = "id") -> None:
        self._prefix = prefix
        self._counter = 0

    def new_id(self) -> str:
        self._counter += 1
        return f"{self._prefix}-{self._counter}"


class FixedClock:
    """Deterministic ``Clock``: always returns the same instant."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now
