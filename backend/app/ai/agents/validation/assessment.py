"""Validation Agent contracts (ES-056).

The typed input and product of the ``validation-agent``
(agent-architecture §6): the agent evaluates an investigation's findings
against their supporting evidence and reports issues in the documented
four-way vocabulary — factual inconsistencies, missing evidence, conflicting
observations, unsupported conclusions. Validation improves trustworthiness
before final decisions are synthesized; it never mutates findings (status
transitions remain the analyst's and the owning service's concern).

These are AI-layer operational structures (not domain objects). The agent is
stateless and consumes an **already-assembled** ``ValidationContext`` — the
snapshots are assembled by the orchestration layer (the Workspace / Context
Builder responsibility); the agent never calls services.
"""

from dataclasses import dataclass
from enum import Enum

from app.ai.errors import ValidationAgentError
from app.domain.identifiers import EvidenceId, FindingId, InvestigationId
from app.domain.value_objects import Confidence


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    """The evidence facts the Validation Agent reasons over."""

    id: EvidenceId
    source: str
    integrity: str
    content: str


@dataclass(frozen=True, slots=True)
class FindingSnapshot:
    """The finding facts the Validation Agent reasons over."""

    id: FindingId
    status: str
    confidence: Confidence
    supporting_evidence: tuple[EvidenceId, ...]


@dataclass(frozen=True, slots=True)
class ValidationContext:
    """An already-assembled snapshot of the material under validation."""

    investigation_id: InvestigationId
    objectives: tuple[str, ...]
    findings: tuple[FindingSnapshot, ...]
    evidence: tuple[EvidenceSnapshot, ...]

    def __post_init__(self) -> None:
        if not self.findings:
            raise ValidationAgentError(
                "Validation requires at least one finding."
            )


class ValidationIssueKind(Enum):
    """The documented validation-issue vocabulary (agent-architecture §6)."""

    FACTUAL_INCONSISTENCY = "factual_inconsistency"
    MISSING_EVIDENCE = "missing_evidence"
    CONFLICTING_OBSERVATIONS = "conflicting_observations"
    UNSUPPORTED_CONCLUSION = "unsupported_conclusion"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One reported issue; ``finding_id`` is None for investigation-wide issues."""

    kind: ValidationIssueKind
    detail: str
    finding_id: FindingId | None = None


@dataclass(frozen=True, slots=True)
class ValidationAssessment:
    """The Validation Agent's product: assessed findings and their issues."""

    investigation_id: InvestigationId
    assessed_findings: tuple[FindingId, ...]
    issues: tuple[ValidationIssue, ...]
    summary: str
