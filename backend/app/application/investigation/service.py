"""Investigation Service.

Application-layer business capability that owns the investigation lifecycle and
manages investigations, evidence, findings and reports (ADR-004 and the
Investigation Service specification). It orchestrates the domain model, depends on
repository ports, performs business validation, and never touches transport or
persistence implementation details.

Logging here is lightweight operational observability for important business
events; it is explicitly not an audit mechanism.
"""

import logging

from app.application.investigation.errors import (
    DuplicateEvidenceError,
    DuplicateInvestigationError,
    DuplicateOutcomeError,
    EvidenceNotFoundError,
    EvidenceOwnershipError,
    EvidencePayloadIntegrityError,
    EvidencePayloadMissingError,
    EvidencePayloadNotFoundError,
    EvidencePayloadStoreUnavailableError,
    FindingNotFoundError,
    InvalidLifecycleTransitionError,
    InvestigationNotFoundError,
    InvestigationValidationError,
    OutcomeNotFoundError,
    ReportNotFoundError,
)
from app.application.investigation.payload_store import (
    PAYLOAD_ADDRESS_PREFIX,
    EvidencePayloadStore,
    is_payload_address,
    payload_address,
)
from app.application.investigation.repositories import (
    EvidenceRepository,
    FindingRepository,
    InvestigationRepository,
    OutcomeRepository,
    ReportRepository,
    TraceRepository,
)
from app.domain.enums import InvestigationStatus
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import EvidenceId, FindingId, InvestigationId, ReportId
from app.domain.investigation import Investigation
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.report import Report
from app.domain.trace import TraceEntry

logger = logging.getLogger(__name__)

# Permitted investigation lifecycle transitions (spec section 10, v1.1.0):
# suspension (Active <-> Suspended) and completion (Completed -> Active on
# significant new evidence) are reversible; Archived is terminal.
_ALLOWED_TRANSITIONS: dict[InvestigationStatus, frozenset[InvestigationStatus]] = {
    InvestigationStatus.CREATED: frozenset({InvestigationStatus.ACTIVE}),
    InvestigationStatus.ACTIVE: frozenset(
        {
            InvestigationStatus.SUSPENDED,
            InvestigationStatus.COMPLETED,
            InvestigationStatus.ARCHIVED,
        }
    ),
    InvestigationStatus.SUSPENDED: frozenset(
        {InvestigationStatus.ACTIVE, InvestigationStatus.ARCHIVED}
    ),
    InvestigationStatus.COMPLETED: frozenset(
        {InvestigationStatus.ACTIVE, InvestigationStatus.ARCHIVED}
    ),
}


class InvestigationService:
    """Manages investigation lifecycle plus its evidence, findings and reports."""

    def __init__(
        self,
        investigations: InvestigationRepository,
        evidence: EvidenceRepository,
        findings: FindingRepository,
        reports: ReportRepository,
        outcomes: OutcomeRepository,
        trace: TraceRepository,
        payloads: EvidencePayloadStore | None = None,
    ) -> None:
        self._investigations = investigations
        self._evidence = evidence
        self._findings = findings
        self._reports = reports
        self._outcomes = outcomes
        self._trace = trace
        # Payload store (ES-060, ADR-015): additive optional dependency —
        # compositions without a payload store keep every prior behavior.
        self._payloads = payloads

    # ------------------------------------------------------------- investigation

    async def create(self, investigation: Investigation) -> Investigation:
        """Validate and persist a new investigation."""

        self._validate_new_investigation(investigation)
        if await self._investigations.get(investigation.id) is not None:
            raise DuplicateInvestigationError(
                f"Investigation '{investigation.id.value}' already exists."
            )
        await self._investigations.add(investigation)
        logger.info(
            "investigation created id=%s status=%s",
            investigation.id.value,
            investigation.status.value,
        )
        return investigation

    async def get(self, investigation_id: InvestigationId) -> Investigation:
        """Return an investigation or raise if it does not exist."""

        return await self._require_investigation(investigation_id)

    async def change_status(
        self, investigation_id: InvestigationId, new_status: InvestigationStatus
    ) -> Investigation:
        """Transition an investigation to a new lifecycle status.

        Only the status field is modified; no other investigation state changes.
        """

        investigation = await self._require_investigation(investigation_id)
        self._validate_transition(investigation.status, new_status)

        previous_status = investigation.status
        investigation.status = new_status
        await self._investigations.update(investigation)
        logger.info(
            "investigation status changed id=%s from=%s to=%s",
            investigation.id.value,
            previous_status.value,
            new_status.value,
        )
        return investigation

    # ------------------------------------------------------------------ evidence

    async def attach_evidence(self, evidence: Evidence) -> Evidence:
        """Attach an evidence item to its investigation after validation."""

        await self._require_investigation(evidence.investigation_id)
        if await self._evidence.get(evidence.id) is not None:
            raise DuplicateEvidenceError(
                f"Evidence '{evidence.id.value}' already exists."
            )
        await self._require_payload_reference(evidence)
        await self._evidence.add(evidence)
        logger.info(
            "evidence attached id=%s investigation=%s",
            evidence.id.value,
            evidence.investigation_id.value,
        )
        return evidence

    async def _require_payload_reference(self, evidence: Evidence) -> None:
        """Validate an address-shaped integrity value against the store.

        Only integrity values claiming to be content addresses (``sha256:``
        prefix, §8b rule 1) participate; opaque interim values (the inline
        content state) stay untouched. Without a composed payload store no
        claim can be checked, so none is enforced.
        """

        address = evidence.integrity.value
        if self._payloads is None or not address.startswith(
            PAYLOAD_ADDRESS_PREFIX
        ):
            return
        if not is_payload_address(address) or not await self._payloads.exists(
            address
        ):
            raise EvidencePayloadMissingError(
                f"Evidence '{evidence.id.value}' references payload "
                f"'{address}' which is not stored."
            )

    async def get_evidence(self, evidence_id: EvidenceId) -> Evidence:
        """Return an evidence item or raise if it does not exist."""

        evidence = await self._evidence.get(evidence_id)
        if evidence is None:
            raise EvidenceNotFoundError(f"Evidence '{evidence_id.value}' not found.")
        return evidence

    async def list_evidence(
        self, investigation_id: InvestigationId
    ) -> tuple[Evidence, ...]:
        """List the evidence attached to an investigation."""

        await self._require_investigation(investigation_id)
        return await self._evidence.list_for_investigation(investigation_id)

    # ---------------------------------------------------------- evidence payload

    async def store_evidence_payload(
        self, investigation_id: InvestigationId, content: bytes
    ) -> str:
        """Store a raw payload for an investigation; return its address.

        Writes the payload store only (AC-14: the evidence record referencing
        the address is a separate single-store operation). Content addressing
        makes the operation idempotent — re-storing existing content is a
        no-op returning the same address (ADR-015 §5).
        """

        await self._require_investigation(investigation_id)
        store = self._require_payload_store()
        address = payload_address(content)
        await store.put(address, content)
        logger.info(
            "evidence payload stored investigation=%s address=%s size=%s",
            investigation_id.value,
            address,
            len(content),
        )
        return address

    async def get_evidence_payload(self, evidence_id: EvidenceId) -> bytes:
        """Return an evidence item's payload, verified against its address.

        The evidence integrity value is the content address (§8b rule 1).
        Evidence carrying an opaque interim integrity value has no payload
        (not found); a dangling address stays observable (not found, §8a); a
        verification mismatch is a distinct integrity fault (Domain Rule 1/9).
        """

        evidence = await self.get_evidence(evidence_id)
        store = self._require_payload_store()
        address = evidence.integrity.value
        if not is_payload_address(address):
            raise EvidencePayloadNotFoundError(
                f"Evidence '{evidence_id.value}' carries no payload address."
            )
        content = await store.get(address)
        if content is None:
            raise EvidencePayloadNotFoundError(
                f"Payload '{address}' of evidence '{evidence_id.value}' "
                f"is not stored."
            )
        if payload_address(content) != address:
            raise EvidencePayloadIntegrityError(
                f"Payload '{address}' of evidence '{evidence_id.value}' "
                f"failed integrity verification."
            )
        return content

    def _require_payload_store(self) -> EvidencePayloadStore:
        if self._payloads is None:
            raise EvidencePayloadStoreUnavailableError(
                "The evidence payload store is not configured."
            )
        return self._payloads

    # ------------------------------------------------------------------- finding

    async def create_finding(self, finding: Finding) -> Finding:
        """Validate and persist a finding for its investigation."""

        await self._require_investigation(finding.investigation_id)
        await self._validate_evidence_references(
            finding.investigation_id, finding.supporting_evidence
        )
        await self._findings.add(finding)
        logger.info(
            "finding created id=%s investigation=%s",
            finding.id.value,
            finding.investigation_id.value,
        )
        return finding

    async def update_finding(self, finding: Finding) -> Finding:
        """Validate and persist changes to an existing finding."""

        if await self._findings.get(finding.id) is None:
            raise FindingNotFoundError(f"Finding '{finding.id.value}' not found.")
        await self._validate_evidence_references(
            finding.investigation_id, finding.supporting_evidence
        )
        await self._findings.update(finding)
        logger.info(
            "finding updated id=%s status=%s",
            finding.id.value,
            finding.status.value,
        )
        return finding

    async def list_findings(
        self, investigation_id: InvestigationId
    ) -> tuple[Finding, ...]:
        """List the findings produced within an investigation."""

        await self._require_investigation(investigation_id)
        return await self._findings.list_for_investigation(investigation_id)

    # -------------------------------------------------------------------- report

    async def create_report(self, report: Report) -> Report:
        """Validate and persist a report for its investigation."""

        await self._require_investigation(report.investigation_id)
        await self._reports.add(report)
        logger.info(
            "report created id=%s investigation=%s",
            report.id.value,
            report.investigation_id.value,
        )
        return report

    async def get_report(self, report_id: ReportId) -> Report:
        """Return a report or raise if it does not exist."""

        report = await self._reports.get(report_id)
        if report is None:
            raise ReportNotFoundError(f"Report '{report_id.value}' not found.")
        return report

    async def list_reports(
        self, investigation_id: InvestigationId
    ) -> tuple[Report, ...]:
        """List the reports produced for an investigation."""

        await self._require_investigation(investigation_id)
        return await self._reports.list_for_investigation(investigation_id)

    # ------------------------------------------------------------------- outcome

    async def create_outcome(
        self, outcome: InvestigationOutcome
    ) -> InvestigationOutcome:
        """Validate and persist the synthesized outcome of an investigation.

        An investigation has at most one outcome (domain-model §16, 0..1).
        """

        await self._require_investigation(outcome.investigation_id)
        existing = await self._outcomes.get_for_investigation(
            outcome.investigation_id
        )
        if existing is not None:
            raise DuplicateOutcomeError(
                f"Investigation '{outcome.investigation_id.value}' already has "
                f"an outcome."
            )
        await self._validate_finding_references(
            outcome.investigation_id, outcome.contributing_findings
        )
        await self._outcomes.add(outcome)
        logger.info(
            "outcome created id=%s investigation=%s",
            outcome.id.value,
            outcome.investigation_id.value,
        )
        return outcome

    async def get_outcome(
        self, investigation_id: InvestigationId
    ) -> InvestigationOutcome:
        """Return an investigation's outcome or raise if none exists."""

        await self._require_investigation(investigation_id)
        outcome = await self._outcomes.get_for_investigation(investigation_id)
        if outcome is None:
            raise OutcomeNotFoundError(
                f"Investigation '{investigation_id.value}' has no outcome."
            )
        return outcome

    # --------------------------------------------------------------------- trace

    async def record_trace(self, entry: TraceEntry) -> TraceEntry:
        """Append an entry to the investigation's explainability trace.

        The trace is append-only; entries are never updated or removed.
        """

        await self._require_investigation(entry.investigation_id)
        if not entry.summary.strip():
            raise InvestigationValidationError(
                "Trace entry summary must not be blank."
            )
        await self._trace.add(entry)
        logger.info(
            "trace entry recorded id=%s investigation=%s kind=%s",
            entry.id.value,
            entry.investigation_id.value,
            entry.kind.value,
        )
        return entry

    async def list_trace(
        self, investigation_id: InvestigationId
    ) -> tuple[TraceEntry, ...]:
        """List the investigation's trace entries in append order."""

        await self._require_investigation(investigation_id)
        return await self._trace.list_for_investigation(investigation_id)

    # ------------------------------------------------------------------- helpers

    async def _require_investigation(
        self, investigation_id: InvestigationId
    ) -> Investigation:
        investigation = await self._investigations.get(investigation_id)
        if investigation is None:
            raise InvestigationNotFoundError(
                f"Investigation '{investigation_id.value}' not found."
            )
        return investigation

    async def _validate_evidence_references(
        self,
        investigation_id: InvestigationId,
        evidence_ids: tuple[EvidenceId, ...],
    ) -> None:
        for evidence_id in evidence_ids:
            evidence = await self._evidence.get(evidence_id)
            if evidence is None:
                raise EvidenceNotFoundError(
                    f"Evidence '{evidence_id.value}' not found."
                )
            if evidence.investigation_id != investigation_id:
                raise EvidenceOwnershipError(
                    f"Evidence '{evidence_id.value}' does not belong to "
                    f"investigation '{investigation_id.value}'."
                )

    async def _validate_finding_references(
        self,
        investigation_id: InvestigationId,
        finding_ids: tuple[FindingId, ...],
    ) -> None:
        for finding_id in finding_ids:
            finding = await self._findings.get(finding_id)
            if finding is None:
                raise FindingNotFoundError(
                    f"Finding '{finding_id.value}' not found."
                )
            if finding.investigation_id != investigation_id:
                raise InvestigationValidationError(
                    f"Finding '{finding_id.value}' does not belong to "
                    f"investigation '{investigation_id.value}'."
                )

    @staticmethod
    def _validate_new_investigation(investigation: Investigation) -> None:
        if not investigation.title.strip():
            raise InvestigationValidationError(
                "Investigation title must not be blank."
            )
        if investigation.status is not InvestigationStatus.CREATED:
            raise InvestigationValidationError(
                "A new investigation must start in the CREATED status."
            )

    @staticmethod
    def _validate_transition(
        current: InvestigationStatus, target: InvestigationStatus
    ) -> None:
        if target not in _ALLOWED_TRANSITIONS.get(current, frozenset()):
            raise InvalidLifecycleTransitionError(
                f"Cannot transition investigation from "
                f"{current.value} to {target.value}."
            )
