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
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.report import Report
from app.domain.repositories import Repository
from app.domain.trace import TraceEntry


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

    async def erase_for_investigation(
        self, investigation_id: InvestigationId
    ) -> None:
        """Tombstone every evidence item of an investigation (ADR-017).

        The end-of-life erasure cascade — the only mutation of otherwise
        immutable evidence (Domain Rule 1); content and source are redacted,
        the content-address integrity value is retained (ES-065).
        """
        ...

    async def list_pending_payload_erasures(
        self, limit: int
    ) -> tuple[Evidence, ...]:
        """Evidence tombstones whose payload bytes are still to be erased.

        The driver of the payload erasure projection (ES-065, ADR-017 §5): the
        tombstone written in the erasure transaction **is** the durable erasure
        intent, so this returns evidence of erased investigations that still
        carry an address-shaped integrity value (their bytes may still exist).
        """
        ...

    async def mark_payload_erased(self, evidence_id: EvidenceId) -> None:
        """Redact an evidence tombstone's payload address once its bytes are gone.

        Completes the payload erasure projection: the reference is replaced by
        the erasure marker, so the projection converges (the item stops being
        pending) and the record no longer points at erased bytes — it resolves
        to an explicit "erased" reference (§8a).
        """
        ...


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


class OutcomeRepository(Repository, Protocol):
    """Persistence operations for InvestigationOutcome (0..1 per investigation)."""

    async def add(self, outcome: InvestigationOutcome) -> None: ...

    async def get_for_investigation(
        self, investigation_id: InvestigationId
    ) -> InvestigationOutcome | None: ...

    async def erase_for_investigation(
        self, investigation_id: InvestigationId
    ) -> None:
        """Tombstone an investigation's outcome, if any (ADR-017).

        Redacts the free-text recommendation, detected conflicts and open
        questions; identifiers, references, confidence and status survive.
        """
        ...


class TraceRepository(Repository, Protocol):
    """Append-only persistence operations for Investigation Trace entries.

    The trace is append-only by contract: no update or delete operation exists
    for business writes. ``erase_for_investigation`` is the sole exception — the
    documented end-of-life erasure path (domain-model.md line 633, ADR-017 §4),
    never a business write. ``list_for_investigation`` returns entries in append
    order.
    """

    async def add(self, entry: TraceEntry) -> None: ...

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[TraceEntry, ...]: ...

    async def erase_for_investigation(
        self, investigation_id: InvestigationId
    ) -> None:
        """Tombstone every trace entry of an investigation (ADR-017).

        Redacts each entry's summary; kind, actor, reference, append order and
        timestamps survive. The end-of-life exception to trace append-only.
        """
        ...
