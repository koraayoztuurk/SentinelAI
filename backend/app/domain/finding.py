"""Finding entity.

A Finding represents an analytical conclusion derived from evidence during an
investigation. Unlike Evidence, it contains interpretation rather than raw facts.
Every Finding must reference at least one supporting Evidence item (Domain Rule 2)
and may correlate entities and relationships, which it references by identifier.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import FindingStatus
from app.domain.exceptions import MissingSupportingEvidenceError
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    RelationshipId,
)
from app.domain.value_objects import ActorRef, Confidence


@dataclass(slots=True)
class Finding:
    """An evidence-backed analytical conclusion within an investigation."""

    id: FindingId
    investigation_id: InvestigationId
    supporting_evidence: tuple[EvidenceId, ...]
    creator: ActorRef
    created_at: datetime
    confidence: Confidence
    status: FindingStatus
    related_entities: tuple[EntityId, ...] = ()
    related_relationships: tuple[RelationshipId, ...] = ()

    def __post_init__(self) -> None:
        if not self.supporting_evidence:
            raise MissingSupportingEvidenceError(
                "Finding must reference at least one supporting evidence item."
            )
