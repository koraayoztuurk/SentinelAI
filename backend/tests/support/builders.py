"""Shared deterministic builders (Test Foundation, ES-032).

Pure constructors for the Investigation-family domain objects with valid defaults.
Each call returns a fresh, independent object and never mutates it afterwards; there
is no shared mutable state and no mutable default arguments (collections default to
immutable tuples, ``FIXED_TIME`` is an immutable ``datetime``), so the builders stay
deterministic and side-effect-free.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from app.application.investigation import InvestigationService
from app.domain.enums import FindingStatus, InvestigationStatus
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    RelationshipId,
    ReportId,
)
from app.domain.investigation import Investigation
from app.domain.report import Report
from app.domain.value_objects import (
    ActorRef,
    Confidence,
    EvidenceIntegrity,
    EvidenceSource,
    Priority,
)
from tests.support.doubles import (
    InMemoryEvidenceRepository,
    InMemoryFindingRepository,
    InMemoryInvestigationRepository,
    InMemoryReportRepository,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def build_investigation(
    investigation_id: str,
    *,
    status: InvestigationStatus = InvestigationStatus.CREATED,
    title: str = "Test investigation",
    owner: str = "analyst-1",
    priority: str = "high",
    created_at: datetime = FIXED_TIME,
) -> Investigation:
    return Investigation(
        id=InvestigationId(investigation_id),
        title=title,
        status=status,
        created_at=created_at,
        owner=ActorRef(owner),
        priority=Priority(priority),
    )


def build_evidence(
    evidence_id: str,
    investigation_id: str,
    *,
    source: str = "edr",
    integrity: str = "verified",
    content: str = "evidence content",
    timestamp: datetime = FIXED_TIME,
) -> Evidence:
    return Evidence(
        id=EvidenceId(evidence_id),
        investigation_id=InvestigationId(investigation_id),
        source=EvidenceSource(source),
        timestamp=timestamp,
        integrity=EvidenceIntegrity(integrity),
        content=content,
    )


def build_finding(
    finding_id: str,
    investigation_id: str,
    *,
    supporting_evidence: Sequence[str] = (),
    creator: str = "analyst-1",
    confidence: float = 0.8,
    status: FindingStatus = FindingStatus.PROPOSED,
    related_entities: Sequence[str] = (),
    related_relationships: Sequence[str] = (),
    created_at: datetime = FIXED_TIME,
) -> Finding:
    return Finding(
        id=FindingId(finding_id),
        investigation_id=InvestigationId(investigation_id),
        supporting_evidence=tuple(EvidenceId(v) for v in supporting_evidence),
        creator=ActorRef(creator),
        created_at=created_at,
        confidence=Confidence(confidence),
        status=status,
        related_entities=tuple(EntityId(v) for v in related_entities),
        related_relationships=tuple(
            RelationshipId(v) for v in related_relationships
        ),
    )


def build_report(
    report_id: str,
    investigation_id: str,
    *,
    author: str = "analyst-1",
    version: int = 1,
    created_at: datetime = FIXED_TIME,
) -> Report:
    return Report(
        id=ReportId(report_id),
        investigation_id=InvestigationId(investigation_id),
        author=ActorRef(author),
        created_at=created_at,
        version=version,
    )


def make_investigation_service() -> InvestigationService:
    """Wire an ``InvestigationService`` over fresh in-memory doubles."""

    return InvestigationService(
        InMemoryInvestigationRepository(),
        InMemoryEvidenceRepository(),
        InMemoryFindingRepository(),
        InMemoryReportRepository(),
    )
