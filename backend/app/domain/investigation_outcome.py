"""Investigation Outcome entity.

An InvestigationOutcome captures the synthesized result produced at the end of the
analysis phase, before a human-readable Report is generated. It references the
findings supporting its conclusions rather than raw evidence, and records detected
conflicts and unresolved questions. It may optionally reference the Report derived
from it.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import InvestigationOutcomeStatus
from app.domain.identifiers import (
    FindingId,
    InvestigationId,
    InvestigationOutcomeId,
    ReportId,
)
from app.domain.value_objects import Confidence


@dataclass(slots=True)
class InvestigationOutcome:
    """The synthesized, finding-backed result of an investigation's analysis phase."""

    id: InvestigationOutcomeId
    investigation_id: InvestigationId
    confidence: Confidence
    recommendation: str
    status: InvestigationOutcomeStatus
    created_at: datetime
    contributing_findings: tuple[FindingId, ...] = ()
    detected_conflicts: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    report_id: ReportId | None = None
