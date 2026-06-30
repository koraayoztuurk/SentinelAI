"""Graph API request/response schemas and mappers.

The request models carry the client-supplied business fields; the response models
are flat projections of the domain objects. All DTO-to-domain and domain-to-DTO
conversion lives here (``to_domain`` / ``from_domain``) so the controllers stay
thin. Entity identifiers are client-supplied (the entity's canonical identity,
Domain Rule 3); relationship identifiers and timestamps are passed in by the
controller from the API's ``IdGenerator`` and ``Clock``.
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.entity import Entity
from app.domain.identifiers import EntityId, EvidenceId, RelationshipId
from app.domain.relationship import Relationship
from app.domain.value_objects import (
    Confidence,
    EntityType,
    RelationshipType,
)

# ---------------------------------------------------------------------- entity


class EntityCreateRequest(BaseModel):
    """Client-supplied fields for creating (or reusing) an entity."""

    id: str
    type: str
    display_name: str
    confidence: float
    source: str
    attributes: dict[str, str] = {}
    aliases: list[str] = []

    def to_domain(self) -> Entity:
        return Entity(
            id=EntityId(self.id),
            type=EntityType(self.type),
            display_name=self.display_name,
            confidence=Confidence(self.confidence),
            source=self.source,
            attributes=dict(self.attributes),
            aliases=tuple(self.aliases),
        )


class EntityAttributesUpdateRequest(BaseModel):
    """Replacement descriptive attributes for an entity."""

    attributes: dict[str, str]


class EntityResponse(BaseModel):
    """Flat projection of an entity."""

    id: str
    type: str
    display_name: str
    confidence: float
    source: str
    attributes: dict[str, str]
    aliases: list[str]

    @classmethod
    def from_domain(cls, entity: Entity) -> "EntityResponse":
        return cls(
            id=entity.id.value,
            type=entity.type.value,
            display_name=entity.display_name,
            confidence=entity.confidence.value,
            source=entity.source,
            attributes=dict(entity.attributes),
            aliases=list(entity.aliases),
        )


# ---------------------------------------------------------------- relationship


class RelationshipCreateRequest(BaseModel):
    """Client-supplied fields for creating a relationship."""

    source_entity_id: str
    target_entity_id: str
    type: str
    confidence: float
    supporting_evidence: list[str]

    def to_domain(self, *, id_value: str, created_at: datetime) -> Relationship:
        return Relationship(
            id=RelationshipId(id_value),
            source_entity_id=EntityId(self.source_entity_id),
            target_entity_id=EntityId(self.target_entity_id),
            type=RelationshipType(self.type),
            confidence=Confidence(self.confidence),
            supporting_evidence=tuple(
                EvidenceId(value) for value in self.supporting_evidence
            ),
            created_at=created_at,
        )


class RelationshipConfidenceUpdateRequest(BaseModel):
    """New confidence for an existing relationship."""

    confidence: float

    def to_confidence(self) -> Confidence:
        return Confidence(self.confidence)


class RelationshipResponse(BaseModel):
    """Flat projection of a relationship."""

    id: str
    source_entity_id: str
    target_entity_id: str
    type: str
    confidence: float
    supporting_evidence: list[str]
    created_at: datetime

    @classmethod
    def from_domain(cls, relationship: Relationship) -> "RelationshipResponse":
        return cls(
            id=relationship.id.value,
            source_entity_id=relationship.source_entity_id.value,
            target_entity_id=relationship.target_entity_id.value,
            type=relationship.type.value,
            confidence=relationship.confidence.value,
            supporting_evidence=[
                e.value for e in relationship.supporting_evidence
            ],
            created_at=relationship.created_at,
        )
