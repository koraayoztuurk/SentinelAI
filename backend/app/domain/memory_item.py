"""Memory Item entity.

A Memory Item represents validated organizational knowledge preserved beyond the
lifetime of a single investigation. It records the investigation it originated
from and may reference supporting evidence, findings, entities and relationships
by identifier, preserving historical traceability.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import MemoryStatus
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    MemoryItemId,
    RelationshipId,
)
from app.domain.value_objects import Confidence, MemoryType


@dataclass(slots=True)
class MemoryItem:
    """Validated organizational knowledge reusable across investigations."""

    id: MemoryItemId
    type: MemoryType
    source_investigation_id: InvestigationId
    confidence: Confidence
    status: MemoryStatus
    created_at: datetime
    version: int = 1
    supporting_evidence: tuple[EvidenceId, ...] = ()
    referenced_findings: tuple[FindingId, ...] = ()
    referenced_entities: tuple[EntityId, ...] = ()
    referenced_relationships: tuple[RelationshipId, ...] = ()
