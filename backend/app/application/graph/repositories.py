"""Repository contract required by the Graph Service.

A single graph repository port: unlike PostgreSQL's independent aggregates, the
graph store holds two tightly interconnected aggregates (relationships reference
entities; traversal and relationship validation span both), so one repository is
the simplest correct contract. It inherits the domain
:class:`~app.domain.repositories.Repository` marker and is implemented by the
infrastructure layer (the concrete Neo4j adapter is introduced by a later
specification). Defining it here keeps the domain model untouched while
preserving the inward dependency direction.
"""

from typing import Protocol

from app.domain.entity import Entity
from app.domain.identifiers import EntityId, RelationshipId
from app.domain.relationship import Relationship
from app.domain.repositories import Repository


class GraphRepository(Repository, Protocol):
    """Persistence operations for the entity/relationship graph."""

    async def add_entity(self, entity: Entity) -> None: ...

    async def get_entity(self, entity_id: EntityId) -> Entity | None: ...

    async def update_entity(self, entity: Entity) -> None: ...

    async def add_relationship(self, relationship: Relationship) -> None: ...

    async def get_relationship(
        self, relationship_id: RelationshipId
    ) -> Relationship | None: ...

    async def update_relationship(self, relationship: Relationship) -> None: ...

    async def list_relationships_for_entity(
        self, entity_id: EntityId
    ) -> tuple[Relationship, ...]: ...

    async def neighbors(
        self, entity_id: EntityId, depth: int, max_nodes: int
    ) -> tuple[Entity, ...]: ...

    async def erase_entity(self, entity: Entity) -> None:
        """Persist an entity tombstone (ES-065, ADR-017 §4).

        The end-of-life write for person-linked graph data: the node keeps its
        stable identifier so incident relationships still resolve to an explicit
        erased node (§8a), while its identifying payload is redacted.
        """
        ...
