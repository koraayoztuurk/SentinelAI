"""Unit tests for the SentinelAI domain model (ES-003).

Plain pytest functions only — no fixtures or shared testing abstractions.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from app.domain import (
    ActorRef,
    Confidence,
    Entity,
    EntityId,
    EntityType,
    Evidence,
    EvidenceId,
    EvidenceIntegrity,
    EvidenceSource,
    Finding,
    FindingId,
    FindingStatus,
    Investigation,
    InvestigationId,
    InvestigationOutcome,
    InvestigationOutcomeId,
    InvestigationOutcomeStatus,
    InvestigationStatus,
    MemoryItem,
    MemoryItemId,
    MemoryStatus,
    MemoryType,
    Priority,
    Relationship,
    RelationshipId,
    RelationshipType,
    Report,
    ReportId,
    Task,
    TaskId,
    TaskStatus,
)
from app.domain.exceptions import (
    BlankValueError,
    InvalidConfidenceError,
    MissingSupportingEvidenceError,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_confidence_accepts_inclusive_bounds() -> None:
    assert Confidence(0.0).value == 0.0
    assert Confidence(1.0).value == 1.0
    assert Confidence(0.5).value == 0.5


def test_confidence_rejects_out_of_range() -> None:
    with pytest.raises(InvalidConfidenceError):
        Confidence(-0.01)
    with pytest.raises(InvalidConfidenceError):
        Confidence(1.01)


def test_identifier_rejects_blank() -> None:
    with pytest.raises(BlankValueError):
        InvestigationId("")
    with pytest.raises(BlankValueError):
        EvidenceId("   ")


def test_string_value_object_rejects_blank() -> None:
    with pytest.raises(BlankValueError):
        EntityType("")
    with pytest.raises(BlankValueError):
        Priority("  ")
    with pytest.raises(BlankValueError):
        EvidenceIntegrity("")


def test_finding_requires_supporting_evidence() -> None:
    with pytest.raises(MissingSupportingEvidenceError):
        Finding(
            id=FindingId("f-1"),
            investigation_id=InvestigationId("inv-1"),
            supporting_evidence=(),
            creator=ActorRef("analyst-1"),
            created_at=_NOW,
            confidence=Confidence(0.8),
            status=FindingStatus.PROPOSED,
        )


def test_finding_with_evidence_is_valid() -> None:
    finding = Finding(
        id=FindingId("f-1"),
        investigation_id=InvestigationId("inv-1"),
        supporting_evidence=(EvidenceId("ev-1"),),
        creator=ActorRef("analyst-1"),
        created_at=_NOW,
        confidence=Confidence(0.8),
        status=FindingStatus.PROPOSED,
    )
    assert finding.supporting_evidence == (EvidenceId("ev-1"),)


def test_relationship_requires_supporting_evidence() -> None:
    with pytest.raises(MissingSupportingEvidenceError):
        Relationship(
            id=RelationshipId("rel-1"),
            source_entity_id=EntityId("ent-1"),
            target_entity_id=EntityId("ent-2"),
            type=RelationshipType("communicates_with"),
            confidence=Confidence(0.6),
            supporting_evidence=(),
            created_at=_NOW,
        )


def test_evidence_is_immutable() -> None:
    evidence = Evidence(
        id=EvidenceId("ev-1"),
        investigation_id=InvestigationId("inv-1"),
        source=EvidenceSource("siem"),
        timestamp=_NOW,
        integrity=EvidenceIntegrity("integrity-token"),
        content="raw log line",
    )
    with pytest.raises(FrozenInstanceError):
        evidence.content = "tampered"  # type: ignore[misc]


def test_all_entities_construct_with_valid_inputs() -> None:
    investigation = Investigation(
        id=InvestigationId("inv-1"),
        title="Suspicious lateral movement",
        status=InvestigationStatus.ACTIVE,
        created_at=_NOW,
        owner=ActorRef("analyst-1"),
        priority=Priority("high"),
    )
    entity = Entity(
        id=EntityId("ent-1"),
        type=EntityType("endpoint"),
        display_name="WS-001",
        confidence=Confidence(0.9),
        source="edr",
    )
    task = Task(
        id=TaskId("task-1"),
        investigation_id=InvestigationId("inv-1"),
        assigned_agent=ActorRef("timeline-agent"),
        status=TaskStatus.PENDING,
        priority=Priority("medium"),
        created_at=_NOW,
    )
    memory_item = MemoryItem(
        id=MemoryItemId("mem-1"),
        type=MemoryType("attack_pattern"),
        source_investigation_id=InvestigationId("inv-1"),
        confidence=Confidence(0.95),
        status=MemoryStatus.VERIFIED,
        created_at=_NOW,
    )
    outcome = InvestigationOutcome(
        id=InvestigationOutcomeId("out-1"),
        investigation_id=InvestigationId("inv-1"),
        confidence=Confidence(0.85),
        recommendation="Escalate to incident response.",
        status=InvestigationOutcomeStatus.SYNTHESIZED,
        created_at=_NOW,
        contributing_findings=(FindingId("f-1"),),
    )
    report = Report(
        id=ReportId("rep-1"),
        investigation_id=InvestigationId("inv-1"),
        author=ActorRef("report-agent"),
        created_at=_NOW,
    )

    assert investigation.status is InvestigationStatus.ACTIVE
    assert entity.attributes == {}
    assert task.dependencies == ()
    assert memory_item.version == 1
    assert outcome.report_id is None
    assert report.version == 1
