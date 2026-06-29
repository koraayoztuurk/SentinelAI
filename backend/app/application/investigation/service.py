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
    EvidenceNotFoundError,
    EvidenceOwnershipError,
    FindingNotFoundError,
    InvalidLifecycleTransitionError,
    InvestigationNotFoundError,
    InvestigationValidationError,
    ReportNotFoundError,
)
from app.application.investigation.repositories import (
    EvidenceRepository,
    FindingRepository,
    InvestigationRepository,
    ReportRepository,
)
from app.domain.enums import InvestigationStatus
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import EvidenceId, InvestigationId, ReportId
from app.domain.investigation import Investigation
from app.domain.report import Report

logger = logging.getLogger(__name__)

# Permitted investigation lifecycle transitions (spec section 10).
_ALLOWED_TRANSITIONS: dict[InvestigationStatus, frozenset[InvestigationStatus]] = {
    InvestigationStatus.CREATED: frozenset({InvestigationStatus.ACTIVE}),
    InvestigationStatus.ACTIVE: frozenset(
        {InvestigationStatus.COMPLETED, InvestigationStatus.ARCHIVED}
    ),
    InvestigationStatus.COMPLETED: frozenset({InvestigationStatus.ARCHIVED}),
}


class InvestigationService:
    """Manages investigation lifecycle plus its evidence, findings and reports."""

    def __init__(
        self,
        investigations: InvestigationRepository,
        evidence: EvidenceRepository,
        findings: FindingRepository,
        reports: ReportRepository,
    ) -> None:
        self._investigations = investigations
        self._evidence = evidence
        self._findings = findings
        self._reports = reports

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
        await self._evidence.add(evidence)
        logger.info(
            "evidence attached id=%s investigation=%s",
            evidence.id.value,
            evidence.investigation_id.value,
        )
        return evidence

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
