"""Graph Service.

Application-layer business capability that owns graph knowledge (entities and
relationships) and isolates the rest of the platform from the graph database
(ADR-004, Graph Service specification). It orchestrates the domain model, depends
on a repository port, performs graph validation, and never interprets graph data
or touches transport/persistence implementation details.

Logging here is lightweight operational observability for important business
events; it is explicitly not an audit mechanism.
"""

import logging

from app.application.graph.errors import (
    EntityNotFoundError,
    RelationshipNotFoundError,
)
from app.application.graph.repositories import GraphRepository
from app.domain.entity import Entity
from app.domain.erasure import tombstone_entity
from app.domain.identifiers import EntityId, RelationshipId
from app.domain.relationship import Relationship
from app.domain.value_objects import Confidence

logger = logging.getLogger(__name__)


class GraphService:
    """Manages entities, relationships and bounded neighbourhood traversal."""

    def __init__(self, graph: GraphRepository) -> None:
        self._graph = graph

    # -------------------------------------------------------------------- entity

    async def get_entity(self, entity_id: EntityId) -> Entity:
        """Return an entity or raise if it does not exist."""

        return await self._require_entity(entity_id)

    async def create_entity(self, entity: Entity) -> Entity:
        """Create an entity, reusing an existing one with the same identity.

        Entity identity is the canonical key (Rule 3). If an entity with the same
        identifier already exists, it is reused rather than duplicated; the
        existing entity is returned unchanged.
        """

        existing = await self._graph.get_entity(entity.id)
        if existing is not None:
            logger.info(
                "entity reused id=%s type=%s",
                existing.id.value,
                existing.type.value,
            )
            return existing

        await self._graph.add_entity(entity)
        logger.info(
            "entity created id=%s type=%s",
            entity.id.value,
            entity.type.value,
        )
        return entity

    async def update_entity_attributes(
        self, entity_id: EntityId, attributes: dict[str, str]
    ) -> Entity:
        """Update only the descriptive attributes of an existing entity."""

        entity = await self._require_entity(entity_id)
        entity.attributes = attributes
        await self._graph.update_entity(entity)
        logger.info("entity attributes updated id=%s", entity.id.value)
        return entity

    async def erase_entity(self, entity_id: EntityId) -> Entity:
        """Erase a person-linked entity: redact its identifying data (ADR-017).

        The right-to-be-forgotten path for graph knowledge (data-lifecycle.md
        §2) — **not** cascaded by investigation erasure, since the Knowledge
        Graph is a shared knowledge layer (§6a) and entities are
        investigation-independent (Domain Rule 8).

        *Which* entities are person-linked is deliberately **not inferred from
        data content**: the caller names the entity by identifier, mirroring the
        scoping rule that a policy attribute is never derived from data
        (authentication-authorization §6a). Mapping obligations to concrete data
        is a deployment/compliance concern (data-lifecycle.md §6).

        The node keeps its identifier so incident relationships still resolve to
        an explicit erased node (§8a); relationships carry only structural
        references and need no redaction. Idempotent: re-erasing yields the same
        tombstone.
        """

        entity = await self._require_entity(entity_id)
        tombstone = tombstone_entity(entity)
        await self._graph.erase_entity(tombstone)
        logger.info("entity erased id=%s", entity_id.value)
        return tombstone

    # -------------------------------------------------------------- relationship

    async def get_relationship(
        self, relationship_id: RelationshipId
    ) -> Relationship:
        """Return a relationship or raise if it does not exist."""

        relationship = await self._graph.get_relationship(relationship_id)
        if relationship is None:
            raise RelationshipNotFoundError(
                f"Relationship '{relationship_id.value}' not found."
            )
        return relationship

    async def create_relationship(
        self, relationship: Relationship
    ) -> Relationship:
        """Create a relationship after validating both endpoint entities exist."""

        await self._require_entity(relationship.source_entity_id)
        await self._require_entity(relationship.target_entity_id)
        await self._graph.add_relationship(relationship)
        logger.info(
            "relationship created id=%s type=%s source=%s target=%s",
            relationship.id.value,
            relationship.type.value,
            relationship.source_entity_id.value,
            relationship.target_entity_id.value,
        )
        return relationship

    async def update_relationship_confidence(
        self, relationship_id: RelationshipId, confidence: Confidence
    ) -> Relationship:
        """Update only the confidence of an existing relationship."""

        relationship = await self.get_relationship(relationship_id)
        relationship.confidence = confidence
        await self._graph.update_relationship(relationship)
        logger.info(
            "relationship confidence updated id=%s",
            relationship.id.value,
        )
        return relationship

    async def list_relationships_for_entity(
        self, entity_id: EntityId
    ) -> tuple[Relationship, ...]:
        """List the relationships incident to an entity."""

        await self._require_entity(entity_id)
        return await self._graph.list_relationships_for_entity(entity_id)

    # ----------------------------------------------------------------- traversal

    async def find_neighbors(
        self, entity_id: EntityId, *, depth: int, max_nodes: int
    ) -> tuple[Entity, ...]:
        """Return entities within ``depth`` hops of the given entity.

        ``depth`` and ``max_nodes`` bound resource usage only: they cap how much
        of the graph is explored and returned. They never alter graph semantics
        or business behaviour.
        """

        await self._require_entity(entity_id)
        return await self._graph.neighbors(entity_id, depth, max_nodes)

    # ------------------------------------------------------------------- helpers

    async def _require_entity(self, entity_id: EntityId) -> Entity:
        entity = await self._graph.get_entity(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Entity '{entity_id.value}' not found.")
        return entity
