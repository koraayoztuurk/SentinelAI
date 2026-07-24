"""Domain ↔ ORM mappers for the Investigation family.

Pure conversion functions between the technology-independent domain objects
and their PostgreSQL row classes. Value objects and enums are flattened to
their stable primitive values on the way in and reconstructed (re-validated)
on the way out; identifier tuples become lists for the array columns and back.
No mapper touches a session or performs I/O.
"""

from app.domain.enums import (
    FindingStatus,
    InvestigationOutcomeStatus,
    InvestigationStatus,
)
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    InvestigationOutcomeId,
    RelationshipId,
    ReportId,
    TenantId,
    TraceEntryId,
)
from app.domain.investigation import Investigation
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.report import Report
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import (
    ActorRef,
    Confidence,
    EvidenceIntegrity,
    EvidenceSource,
    Priority,
)
from app.infrastructure.persistence.postgres.investigation.orm import (
    EvidenceRow,
    FindingRow,
    InvestigationOutcomeRow,
    InvestigationRow,
    ReportRow,
    TraceEntryRow,
)

# ---------------------------------------------------------------- investigation


def investigation_to_row(investigation: Investigation) -> InvestigationRow:
    return InvestigationRow(
        id=investigation.id.value,
        title=investigation.title,
        status=investigation.status.value,
        tenant=investigation.tenant.value,
        created_at=investigation.created_at,
        owner=investigation.owner.value,
        priority=investigation.priority.value,
        erased_at=investigation.erased_at,
    )


def investigation_to_domain(row: InvestigationRow) -> Investigation:
    return Investigation(
        id=InvestigationId(row.id),
        title=row.title,
        status=InvestigationStatus(row.status),
        created_at=row.created_at,
        owner=ActorRef(row.owner),
        priority=Priority(row.priority),
        tenant=TenantId(row.tenant),
        erased_at=row.erased_at,
    )


# --------------------------------------------------------------------- evidence


def evidence_to_row(evidence: Evidence) -> EvidenceRow:
    return EvidenceRow(
        id=evidence.id.value,
        investigation_id=evidence.investigation_id.value,
        source=evidence.source.value,
        timestamp=evidence.timestamp,
        integrity=evidence.integrity.value,
        content=evidence.content,
    )


def evidence_to_domain(row: EvidenceRow) -> Evidence:
    return Evidence(
        id=EvidenceId(row.id),
        investigation_id=InvestigationId(row.investigation_id),
        source=EvidenceSource(row.source),
        timestamp=row.timestamp,
        integrity=EvidenceIntegrity(row.integrity),
        content=row.content,
    )


# ---------------------------------------------------------------------- finding


def finding_to_row(finding: Finding) -> FindingRow:
    return FindingRow(
        id=finding.id.value,
        investigation_id=finding.investigation_id.value,
        supporting_evidence=[e.value for e in finding.supporting_evidence],
        creator=finding.creator.value,
        created_at=finding.created_at,
        confidence=finding.confidence.value,
        status=finding.status.value,
        related_entities=[e.value for e in finding.related_entities],
        related_relationships=[r.value for r in finding.related_relationships],
    )


def finding_to_domain(row: FindingRow) -> Finding:
    return Finding(
        id=FindingId(row.id),
        investigation_id=InvestigationId(row.investigation_id),
        supporting_evidence=tuple(EvidenceId(v) for v in row.supporting_evidence),
        creator=ActorRef(row.creator),
        created_at=row.created_at,
        confidence=Confidence(row.confidence),
        status=FindingStatus(row.status),
        related_entities=tuple(EntityId(v) for v in row.related_entities),
        related_relationships=tuple(
            RelationshipId(v) for v in row.related_relationships
        ),
    )


# ----------------------------------------------------------------------- report


def report_to_row(report: Report) -> ReportRow:
    return ReportRow(
        id=report.id.value,
        investigation_id=report.investigation_id.value,
        author=report.author.value,
        created_at=report.created_at,
        version=report.version,
    )


def report_to_domain(row: ReportRow) -> Report:
    return Report(
        id=ReportId(row.id),
        investigation_id=InvestigationId(row.investigation_id),
        author=ActorRef(row.author),
        created_at=row.created_at,
        version=row.version,
    )


# ---------------------------------------------------------------------- outcome


def outcome_to_row(outcome: InvestigationOutcome) -> InvestigationOutcomeRow:
    return InvestigationOutcomeRow(
        id=outcome.id.value,
        investigation_id=outcome.investigation_id.value,
        confidence=outcome.confidence.value,
        recommendation=outcome.recommendation,
        status=outcome.status.value,
        created_at=outcome.created_at,
        contributing_findings=[f.value for f in outcome.contributing_findings],
        detected_conflicts=list(outcome.detected_conflicts),
        open_questions=list(outcome.open_questions),
        report_id=outcome.report_id.value if outcome.report_id else None,
    )


def outcome_to_domain(row: InvestigationOutcomeRow) -> InvestigationOutcome:
    return InvestigationOutcome(
        id=InvestigationOutcomeId(row.id),
        investigation_id=InvestigationId(row.investigation_id),
        confidence=Confidence(row.confidence),
        recommendation=row.recommendation,
        status=InvestigationOutcomeStatus(row.status),
        created_at=row.created_at,
        contributing_findings=tuple(
            FindingId(v) for v in row.contributing_findings
        ),
        detected_conflicts=tuple(row.detected_conflicts),
        open_questions=tuple(row.open_questions),
        report_id=ReportId(row.report_id) if row.report_id else None,
    )


# ------------------------------------------------------------------------ trace


def trace_entry_to_row(entry: TraceEntry) -> TraceEntryRow:
    return TraceEntryRow(
        id=entry.id.value,
        investigation_id=entry.investigation_id.value,
        kind=entry.kind.value,
        actor=entry.actor.value,
        summary=entry.summary,
        reference=entry.reference,
        created_at=entry.created_at,
    )


def trace_entry_to_domain(row: TraceEntryRow) -> TraceEntry:
    return TraceEntry(
        id=TraceEntryId(row.id),
        investigation_id=InvestigationId(row.investigation_id),
        kind=TraceEntryKind(row.kind),
        actor=ActorRef(row.actor),
        summary=row.summary,
        reference=row.reference,
        created_at=row.created_at,
    )
