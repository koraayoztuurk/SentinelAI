"""Explicit-contract unavailable graph repository (ES-042).

The first vertical slice binds one authoritative store (PostgreSQL); the
concrete Neo4j adapter follows a later slice (ES-006 technical debt). Where a
graph repository is nevertheless required at runtime — the Planner Service
composition — this adapter realizes the ``GraphRepository`` port with an
explicit contract: every operation raises
:class:`~app.application.graph.errors.GraphStoreUnavailableError` with its
stable code. The Planner Service isolates that failure into a contained
failed execution result (planner-service §8), which is the slice's living
proof of the failure-isolation contract; the Graph API itself stays unbound
(503).
"""

from typing import NoReturn

from app.application.graph.errors import GraphStoreUnavailableError
from app.domain.entity import Entity
from app.domain.identifiers import EntityId, RelationshipId
from app.domain.relationship import Relationship


class UnavailableGraphRepository:
    """``GraphRepository`` adapter whose store is absent from the deployment."""

    @staticmethod
    def _unavailable() -> NoReturn:
        raise GraphStoreUnavailableError(
            "The graph store is not available in this deployment."
        )

    async def add_entity(self, entity: Entity) -> None:
        self._unavailable()

    async def get_entity(self, entity_id: EntityId) -> Entity | None:
        self._unavailable()

    async def update_entity(self, entity: Entity) -> None:
        self._unavailable()

    async def add_relationship(self, relationship: Relationship) -> None:
        self._unavailable()

    async def get_relationship(
        self, relationship_id: RelationshipId
    ) -> Relationship | None:
        self._unavailable()

    async def update_relationship(self, relationship: Relationship) -> None:
        self._unavailable()

    async def list_relationships_for_entity(
        self, entity_id: EntityId
    ) -> tuple[Relationship, ...]:
        self._unavailable()

    async def neighbors(
        self, entity_id: EntityId, depth: int, max_nodes: int
    ) -> tuple[Entity, ...]:
        self._unavailable()
