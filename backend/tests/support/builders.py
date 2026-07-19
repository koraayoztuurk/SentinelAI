"""Shared deterministic builders (Test Foundation, ES-032).

Pure constructors for the Investigation-family domain objects with valid defaults.
Each call returns a fresh, independent object and never mutates it afterwards; there
is no shared mutable state and no mutable default arguments (collections default to
immutable tuples, ``FIXED_TIME`` is an immutable ``datetime``), so the builders stay
deterministic and side-effect-free.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from app.application.graph import GraphService
from app.application.investigation import (
    EvidencePayloadStore,
    InvestigationService,
)
from app.application.memory import MemoryService
from app.domain.entity import Entity
from app.domain.enums import FindingStatus, InvestigationStatus, MemoryStatus
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    MemoryItemId,
    RelationshipId,
    ReportId,
    TenantId,
)
from app.domain.investigation import Investigation
from app.domain.memory_item import MemoryItem
from app.domain.relationship import Relationship
from app.domain.report import Report
from app.domain.value_objects import (
    ActorRef,
    Confidence,
    EntityType,
    EvidenceIntegrity,
    EvidenceSource,
    MemoryType,
    Priority,
    RelationshipType,
)
from tests.support.doubles import (
    InMemoryEvidenceRepository,
    InMemoryFindingRepository,
    InMemoryGraphRepository,
    InMemoryInvestigationRepository,
    InMemoryMemoryRepository,
    InMemoryOutcomeRepository,
    InMemoryReportRepository,
    InMemoryTraceRepository,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def build_investigation(
    investigation_id: str,
    *,
    status: InvestigationStatus = InvestigationStatus.CREATED,
    title: str = "Test investigation",
    owner: str = "analyst-1",
    priority: str = "high",
    tenant: str = "default",
    created_at: datetime = FIXED_TIME,
) -> Investigation:
    return Investigation(
        id=InvestigationId(investigation_id),
        title=title,
        status=status,
        created_at=created_at,
        owner=ActorRef(owner),
        priority=Priority(priority),
        tenant=TenantId(tenant),
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


def build_entity(
    entity_id: str,
    *,
    type_value: str = "endpoint",
    display_name: str = "node",
    confidence: float = 0.9,
    source: str = "edr",
) -> Entity:
    return Entity(
        id=EntityId(entity_id),
        type=EntityType(type_value),
        display_name=display_name,
        confidence=Confidence(confidence),
        source=source,
    )


def build_relationship(
    relationship_id: str,
    source_entity_id: str,
    target_entity_id: str,
    *,
    type_value: str = "communicates_with",
    confidence: float = 0.8,
    supporting_evidence: Sequence[str] = ("ev-1",),
    created_at: datetime = FIXED_TIME,
) -> Relationship:
    return Relationship(
        id=RelationshipId(relationship_id),
        source_entity_id=EntityId(source_entity_id),
        target_entity_id=EntityId(target_entity_id),
        type=RelationshipType(type_value),
        confidence=Confidence(confidence),
        supporting_evidence=tuple(EvidenceId(v) for v in supporting_evidence),
        created_at=created_at,
    )


def build_memory_item(
    memory_id: str,
    *,
    type_value: str = "attack_pattern",
    source_investigation_id: str = "inv-1",
    confidence: float = 0.9,
    status: MemoryStatus = MemoryStatus.CANDIDATE,
    version: int = 1,
    content: str = "",
    created_at: datetime = FIXED_TIME,
) -> MemoryItem:
    return MemoryItem(
        id=MemoryItemId(memory_id),
        type=MemoryType(type_value),
        source_investigation_id=InvestigationId(source_investigation_id),
        confidence=Confidence(confidence),
        status=status,
        created_at=created_at,
        version=version,
        content=content,
    )


def make_investigation_service(
    payloads: EvidencePayloadStore | None = None,
) -> InvestigationService:
    """Wire an ``InvestigationService`` over fresh in-memory doubles."""

    return InvestigationService(
        InMemoryInvestigationRepository(),
        InMemoryEvidenceRepository(),
        InMemoryFindingRepository(),
        InMemoryReportRepository(),
        InMemoryOutcomeRepository(),
        InMemoryTraceRepository(),
        payloads=payloads,
    )


def make_graph_service() -> GraphService:
    """Wire a ``GraphService`` over a fresh in-memory graph repository."""

    return GraphService(InMemoryGraphRepository())


def make_memory_service() -> MemoryService:
    """Wire a ``MemoryService`` over a fresh in-memory memory repository."""

    return MemoryService(InMemoryMemoryRepository())
