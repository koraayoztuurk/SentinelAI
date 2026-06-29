"""Unit tests for the Graph Service (ES-006).

Plain pytest functions with a minimal dict-backed in-memory graph repository
double. No live database is required.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.application.graph import (
    EntityNotFoundError,
    GraphService,
    RelationshipNotFoundError,
)
from app.domain.entity import Entity
from app.domain.identifiers import EntityId, EvidenceId, RelationshipId
from app.domain.relationship import Relationship
from app.domain.value_objects import (
    Confidence,
    EntityType,
    RelationshipType,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


# --------------------------------------------------------------- in-memory double


class InMemoryGraphRepository:
    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}

    async def add_entity(self, entity: Entity) -> None:
        self._entities[entity.id.value] = entity

    async def get_entity(self, entity_id: EntityId) -> Entity | None:
        return self._entities.get(entity_id.value)

    async def update_entity(self, entity: Entity) -> None:
        self._entities[entity.id.value] = entity

    async def add_relationship(self, relationship: Relationship) -> None:
        self._relationships[relationship.id.value] = relationship

    async def get_relationship(
        self, relationship_id: RelationshipId
    ) -> Relationship | None:
        return self._relationships.get(relationship_id.value)

    async def update_relationship(self, relationship: Relationship) -> None:
        self._relationships[relationship.id.value] = relationship

    async def list_relationships_for_entity(
        self, entity_id: EntityId
    ) -> tuple[Relationship, ...]:
        return tuple(
            r
            for r in self._relationships.values()
            if entity_id in (r.source_entity_id, r.target_entity_id)
        )

    async def neighbors(
        self, entity_id: EntityId, depth: int, max_nodes: int
    ) -> tuple[Entity, ...]:
        visited: set[str] = {entity_id.value}
        frontier: list[EntityId] = [entity_id]
        result: list[Entity] = []
        for _ in range(depth):
            next_frontier: list[EntityId] = []
            for current in frontier:
                for relationship in self._relationships.values():
                    neighbor_id: EntityId | None = None
                    if relationship.source_entity_id == current:
                        neighbor_id = relationship.target_entity_id
                    elif relationship.target_entity_id == current:
                        neighbor_id = relationship.source_entity_id
                    if neighbor_id is None or neighbor_id.value in visited:
                        continue
                    visited.add(neighbor_id.value)
                    entity = self._entities.get(neighbor_id.value)
                    if entity is not None:
                        result.append(entity)
                        next_frontier.append(neighbor_id)
                    if len(result) >= max_nodes:
                        return tuple(result)
            frontier = next_frontier
        return tuple(result)


# ------------------------------------------------------------------------ builders


def _entity(entity_id: str, entity_type: str = "endpoint") -> Entity:
    return Entity(
        id=EntityId(entity_id),
        type=EntityType(entity_type),
        display_name="node",
        confidence=Confidence(0.9),
        source="edr",
    )


def _relationship(
    relationship_id: str,
    source_id: str,
    target_id: str,
    confidence: float = 0.8,
) -> Relationship:
    return Relationship(
        id=RelationshipId(relationship_id),
        source_entity_id=EntityId(source_id),
        target_entity_id=EntityId(target_id),
        type=RelationshipType("communicates_with"),
        confidence=Confidence(confidence),
        supporting_evidence=(EvidenceId("ev-1"),),
        created_at=_NOW,
    )


# -------------------------------------------------------------------------- entity


def test_create_entity_and_get() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        await service.create_entity(_entity("e-1"))
        loaded = await service.get_entity(EntityId("e-1"))
        assert loaded.id == EntityId("e-1")

    asyncio.run(scenario())


def test_create_entity_reuses_existing() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        await service.create_entity(_entity("e-1", "endpoint"))
        reused = await service.create_entity(_entity("e-1", "server"))
        # The existing entity is reused unchanged, not overwritten.
        assert reused.type == EntityType("endpoint")

    asyncio.run(scenario())


def test_update_entity_attributes_only() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        original = _entity("e-1")
        await service.create_entity(original)
        updated = await service.update_entity_attributes(
            EntityId("e-1"), {"os": "windows"}
        )
        assert updated.attributes == {"os": "windows"}
        assert updated.type == original.type
        assert updated.display_name == original.display_name
        assert updated.confidence == original.confidence

    asyncio.run(scenario())


def test_get_unknown_entity_raises() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        with pytest.raises(EntityNotFoundError):
            await service.get_entity(EntityId("missing"))

    asyncio.run(scenario())


def test_update_unknown_entity_raises() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        with pytest.raises(EntityNotFoundError):
            await service.update_entity_attributes(EntityId("missing"), {})

    asyncio.run(scenario())


# -------------------------------------------------------------------- relationship


def test_create_relationship_and_get() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        await service.create_entity(_entity("e-1"))
        await service.create_entity(_entity("e-2"))
        await service.create_relationship(_relationship("r-1", "e-1", "e-2"))
        loaded = await service.get_relationship(RelationshipId("r-1"))
        assert loaded.id == RelationshipId("r-1")

    asyncio.run(scenario())


def test_create_relationship_missing_source_raises() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        await service.create_entity(_entity("e-2"))
        with pytest.raises(EntityNotFoundError):
            await service.create_relationship(_relationship("r-1", "e-1", "e-2"))

    asyncio.run(scenario())


def test_create_relationship_missing_target_raises() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        await service.create_entity(_entity("e-1"))
        with pytest.raises(EntityNotFoundError):
            await service.create_relationship(_relationship("r-1", "e-1", "e-2"))

    asyncio.run(scenario())


def test_update_relationship_confidence_only() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        await service.create_entity(_entity("e-1"))
        await service.create_entity(_entity("e-2"))
        await service.create_relationship(_relationship("r-1", "e-1", "e-2", 0.5))
        updated = await service.update_relationship_confidence(
            RelationshipId("r-1"), Confidence(0.95)
        )
        assert updated.confidence == Confidence(0.95)
        assert updated.source_entity_id == EntityId("e-1")
        assert updated.target_entity_id == EntityId("e-2")

    asyncio.run(scenario())


def test_get_unknown_relationship_raises() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        with pytest.raises(RelationshipNotFoundError):
            await service.get_relationship(RelationshipId("missing"))

    asyncio.run(scenario())


def test_list_relationships_for_entity() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        for entity_id in ("e-1", "e-2", "e-3"):
            await service.create_entity(_entity(entity_id))
        await service.create_relationship(_relationship("r-1", "e-1", "e-2"))
        await service.create_relationship(_relationship("r-2", "e-3", "e-1"))
        listed = await service.list_relationships_for_entity(EntityId("e-1"))
        assert len(listed) == 2

    asyncio.run(scenario())


# ----------------------------------------------------------------------- traversal


def test_find_neighbors_respects_depth() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        for entity_id in ("e-1", "e-2", "e-3"):
            await service.create_entity(_entity(entity_id))
        await service.create_relationship(_relationship("r-1", "e-1", "e-2"))
        await service.create_relationship(_relationship("r-2", "e-2", "e-3"))

        one_hop = await service.find_neighbors(
            EntityId("e-1"), depth=1, max_nodes=10
        )
        assert {e.id.value for e in one_hop} == {"e-2"}

        two_hop = await service.find_neighbors(
            EntityId("e-1"), depth=2, max_nodes=10
        )
        assert {e.id.value for e in two_hop} == {"e-2", "e-3"}

    asyncio.run(scenario())


def test_find_neighbors_respects_max_nodes() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        for entity_id in ("e-1", "e-2", "e-3", "e-4"):
            await service.create_entity(_entity(entity_id))
        await service.create_relationship(_relationship("r-1", "e-1", "e-2"))
        await service.create_relationship(_relationship("r-2", "e-1", "e-3"))
        await service.create_relationship(_relationship("r-3", "e-1", "e-4"))

        bounded = await service.find_neighbors(
            EntityId("e-1"), depth=1, max_nodes=2
        )
        assert len(bounded) == 2

    asyncio.run(scenario())


def test_find_neighbors_unknown_entity_raises() -> None:
    async def scenario() -> None:
        service = GraphService(InMemoryGraphRepository())
        with pytest.raises(EntityNotFoundError):
            await service.find_neighbors(EntityId("missing"), depth=1, max_nodes=5)

    asyncio.run(scenario())
