"""Memory API request/response schemas and mappers.

The request models carry the client-supplied business fields; the response model is
a flat projection of the domain object. All DTO-to-domain and domain-to-DTO
conversion lives here (``to_domain`` / ``from_domain``) so the controllers stay
thin. The Memory Item identifier is API-generated on create and always taken from
the path on update — the request body never defines a second identifier. The
``version`` and ``created_at`` are API-generated on create (version 1) and
client-supplied on update (the service enforces sequential versioning).
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import MemoryStatus
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    MemoryItemId,
    RelationshipId,
)
from app.domain.memory_item import MemoryItem
from app.domain.value_objects import Confidence, MemoryType


def _evidence(values: list[str]) -> tuple[EvidenceId, ...]:
    return tuple(EvidenceId(value) for value in values)


def _findings(values: list[str]) -> tuple[FindingId, ...]:
    return tuple(FindingId(value) for value in values)


def _entities(values: list[str]) -> tuple[EntityId, ...]:
    return tuple(EntityId(value) for value in values)


def _relationships(values: list[str]) -> tuple[RelationshipId, ...]:
    return tuple(RelationshipId(value) for value in values)


class MemoryCreateRequest(BaseModel):
    """Client-supplied fields for creating a Memory Item."""

    type: str
    source_investigation_id: str
    confidence: float
    status: MemoryStatus
    supporting_evidence: list[str] = []
    referenced_findings: list[str] = []
    referenced_entities: list[str] = []
    referenced_relationships: list[str] = []

    def to_domain(self, *, id_value: str, created_at: datetime) -> MemoryItem:
        return MemoryItem(
            id=MemoryItemId(id_value),
            type=MemoryType(self.type),
            source_investigation_id=InvestigationId(self.source_investigation_id),
            confidence=Confidence(self.confidence),
            status=self.status,
            created_at=created_at,
            version=1,
            supporting_evidence=_evidence(self.supporting_evidence),
            referenced_findings=_findings(self.referenced_findings),
            referenced_entities=_entities(self.referenced_entities),
            referenced_relationships=_relationships(self.referenced_relationships),
        )


class MemoryUpdateRequest(BaseModel):
    """Full Memory Item representation supplied on update (PUT semantics).

    The identifier is never part of the body: it is taken from the path. The
    ``version`` must immediately follow the latest persisted version.
    """

    type: str
    source_investigation_id: str
    confidence: float
    status: MemoryStatus
    version: int
    created_at: datetime
    supporting_evidence: list[str] = []
    referenced_findings: list[str] = []
    referenced_entities: list[str] = []
    referenced_relationships: list[str] = []

    def to_domain(self, *, id_value: str) -> MemoryItem:
        return MemoryItem(
            id=MemoryItemId(id_value),
            type=MemoryType(self.type),
            source_investigation_id=InvestigationId(self.source_investigation_id),
            confidence=Confidence(self.confidence),
            status=self.status,
            created_at=self.created_at,
            version=self.version,
            supporting_evidence=_evidence(self.supporting_evidence),
            referenced_findings=_findings(self.referenced_findings),
            referenced_entities=_entities(self.referenced_entities),
            referenced_relationships=_relationships(self.referenced_relationships),
        )


class MemoryItemResponse(BaseModel):
    """Flat projection of a Memory Item."""

    id: str
    type: str
    source_investigation_id: str
    confidence: float
    status: str
    created_at: datetime
    version: int
    supporting_evidence: list[str]
    referenced_findings: list[str]
    referenced_entities: list[str]
    referenced_relationships: list[str]

    @classmethod
    def from_domain(cls, item: MemoryItem) -> "MemoryItemResponse":
        return cls(
            id=item.id.value,
            type=item.type.value,
            source_investigation_id=item.source_investigation_id.value,
            confidence=item.confidence.value,
            status=item.status.value,
            created_at=item.created_at,
            version=item.version,
            supporting_evidence=[e.value for e in item.supporting_evidence],
            referenced_findings=[f.value for f in item.referenced_findings],
            referenced_entities=[e.value for e in item.referenced_entities],
            referenced_relationships=[
                r.value for r in item.referenced_relationships
            ],
        )
