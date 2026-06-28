"""Relationship entity.

A Relationship describes a meaningful, evidence-backed connection between two
entities (Entity to Entity only). Every relationship must reference at least one
supporting Evidence item (Domain Rule 4) and preserves its origin for traceability.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.exceptions import MissingSupportingEvidenceError
from app.domain.identifiers import EntityId, EvidenceId, RelationshipId
from app.domain.value_objects import Confidence, RelationshipType


@dataclass(slots=True)
class Relationship:
    """An evidence-backed, directed connection between two entities."""

    id: RelationshipId
    source_entity_id: EntityId
    target_entity_id: EntityId
    type: RelationshipType
    confidence: Confidence
    supporting_evidence: tuple[EvidenceId, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.supporting_evidence:
            raise MissingSupportingEvidenceError(
                "Relationship must reference at least one supporting evidence item."
            )
