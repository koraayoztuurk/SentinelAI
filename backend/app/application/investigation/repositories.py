"""Repository contracts required by the Investigation Service.

These per-aggregate ports define the persistence operations the Investigation
Service depends on. They inherit the domain :class:`~app.domain.repositories.Repository`
marker and are implemented by the infrastructure layer (the concrete PostgreSQL
adapter is introduced by a later specification). Defining them here keeps the
domain model untouched while preserving the inward dependency direction:
infrastructure depends on these application-defined ports, not the reverse.
"""

from typing import Protocol

from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import EvidenceId, FindingId, InvestigationId, ReportId
from app.domain.investigation import Investigation
from app.domain.report import Report
from app.domain.repositories import Repository


class InvestigationRepository(Repository, Protocol):
    """Persistence operations for Investigation aggregates."""

    async def add(self, investigation: Investigation) -> None: ...

    async def get(
        self, investigation_id: InvestigationId
    ) -> Investigation | None: ...

    async def update(self, investigation: Investigation) -> None: ...


class EvidenceRepository(Repository, Protocol):
    """Persistence operations for Evidence owned by the Investigation Service."""

    async def add(self, evidence: Evidence) -> None: ...

    async def get(self, evidence_id: EvidenceId) -> Evidence | None: ...

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Evidence, ...]: ...


class FindingRepository(Repository, Protocol):
    """Persistence operations for Finding aggregates."""

    async def add(self, finding: Finding) -> None: ...

    async def get(self, finding_id: FindingId) -> Finding | None: ...

    async def update(self, finding: Finding) -> None: ...

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Finding, ...]: ...


class ReportRepository(Repository, Protocol):
    """Persistence operations for Report aggregates."""

    async def add(self, report: Report) -> None: ...

    async def get(self, report_id: ReportId) -> Report | None: ...

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Report, ...]: ...
