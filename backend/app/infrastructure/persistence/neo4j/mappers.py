"""Domain ↔ Neo4j record mappers for the graph (ES-048).

Pure conversion between the technology-independent Entity/Relationship domain
objects and their Neo4j property maps. Value objects and enums are flattened to
primitives on the way in and re-validated on the way out.

Two shape decisions, both to keep relationship semantic types out of the graph
structure (so the type vocabulary stays deferrable, per graph-service §11a and
the tracker):

- ``Entity.attributes`` (a ``dict[str, str]``) is stored as a JSON string —
  Neo4j properties cannot nest a map. ``aliases`` is a native string list.
- A relationship is a single Neo4j type ``REL`` whose domain ``type`` is a
  property; endpoints are the connected ``Entity`` nodes (their ids read from
  ``startNode``/``endNode``).
"""

import json
from datetime import datetime
from typing import Any

from app.domain.entity import Entity
from app.domain.identifiers import EntityId, EvidenceId, RelationshipId
from app.domain.relationship import Relationship
from app.domain.value_objects import Confidence, EntityType, RelationshipType


def entity_to_properties(entity: Entity) -> dict[str, Any]:
    return {
        "id": entity.id.value,
        "type": entity.type.value,
        "display_name": entity.display_name,
        "confidence": entity.confidence.value,
        "source": entity.source,
        "attributes_json": json.dumps(entity.attributes, sort_keys=True),
        "aliases": list(entity.aliases),
    }


def entity_from_node(node: dict[str, Any]) -> Entity:
    raw_attributes = node.get("attributes_json") or "{}"
    attributes = json.loads(raw_attributes)
    return Entity(
        id=EntityId(node["id"]),
        type=EntityType(node["type"]),
        display_name=node["display_name"],
        confidence=Confidence(node["confidence"]),
        source=node["source"],
        attributes={str(k): str(v) for k, v in attributes.items()},
        aliases=tuple(node.get("aliases") or ()),
    )


def relationship_to_properties(relationship: Relationship) -> dict[str, Any]:
    return {
        "id": relationship.id.value,
        "type": relationship.type.value,
        "confidence": relationship.confidence.value,
        "supporting_evidence": [e.value for e in relationship.supporting_evidence],
        "created_at": relationship.created_at,
    }


def relationship_from_record(
    rel: dict[str, Any], source_id: str, target_id: str
) -> Relationship:
    created_at = rel["created_at"]
    # The driver returns a neo4j.time.DateTime; normalize to a native datetime.
    if not isinstance(created_at, datetime):
        created_at = created_at.to_native()
    return Relationship(
        id=RelationshipId(rel["id"]),
        source_entity_id=EntityId(source_id),
        target_entity_id=EntityId(target_id),
        type=RelationshipType(rel["type"]),
        confidence=Confidence(rel["confidence"]),
        supporting_evidence=tuple(
            EvidenceId(v) for v in rel.get("supporting_evidence") or ()
        ),
        created_at=created_at,
    )
