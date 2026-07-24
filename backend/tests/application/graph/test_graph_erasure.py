"""Tests for person-linked graph entity erasure (ES-065, ADR-017 §4).

The right-to-be-forgotten path for the Knowledge Graph: the caller names the
entity by identifier (person-linkage is never inferred from data content), the
node keeps its identifier so incident relationships still resolve to an explicit
erased node (§8a), and the identifying payload is redacted.
"""

import asyncio

import pytest

from app.application.graph import EntityNotFoundError
from app.domain.entity import Entity
from app.domain.erasure import REDACTED
from app.domain.identifiers import EntityId
from app.domain.value_objects import Confidence, EntityType
from tests.support.builders import (
    build_entity,
    build_relationship,
    make_graph_service,
)


def _person(entity_id: str) -> Entity:
    return Entity(
        id=EntityId(entity_id),
        type=EntityType("user"),
        display_name="jane.doe@acme.example",
        confidence=Confidence(0.9),
        source="identity-provider",
        attributes={"department": "finance", "manager": "john.roe"},
        aliases=("jdoe", "jane.d"),
    )


def test_erase_entity_redacts_identifying_data() -> None:
    async def scenario() -> None:
        service = make_graph_service()
        await service.create_entity(_person("ent-1"))

        tombstone = await service.erase_entity(EntityId("ent-1"))

        assert tombstone.display_name == REDACTED
        assert tombstone.attributes == {}
        assert tombstone.aliases == ()
        # Correlation structure survives so references still resolve (§8a).
        assert tombstone.id == EntityId("ent-1")
        assert tombstone.type.value == "user"
        assert tombstone.confidence.value == 0.9

        # The tombstone is what the store now returns.
        stored = await service.get_entity(EntityId("ent-1"))
        assert stored.display_name == REDACTED

    asyncio.run(scenario())


def test_erased_entity_still_resolves_for_its_relationships() -> None:
    async def scenario() -> None:
        service = make_graph_service()
        await service.create_entity(_person("ent-1"))
        await service.create_entity(build_entity("ent-2"))
        await service.create_relationship(
            build_relationship("rel-1", "ent-1", "ent-2")
        )

        await service.erase_entity(EntityId("ent-1"))

        # The node is tombstoned, not deleted: the relationship still lists.
        relationships = await service.list_relationships_for_entity(
            EntityId("ent-1")
        )
        assert [r.id.value for r in relationships] == ["rel-1"]
        # Relationships carry only structural references — nothing to redact.
        assert relationships[0].type.value == "communicates_with"

    asyncio.run(scenario())


def test_erase_entity_is_idempotent() -> None:
    async def scenario() -> None:
        service = make_graph_service()
        await service.create_entity(_person("ent-1"))

        first = await service.erase_entity(EntityId("ent-1"))
        second = await service.erase_entity(EntityId("ent-1"))

        assert first.display_name == second.display_name == REDACTED
        assert second.attributes == {}

    asyncio.run(scenario())


def test_erase_unknown_entity_raises() -> None:
    async def scenario() -> None:
        service = make_graph_service()
        with pytest.raises(EntityNotFoundError):
            await service.erase_entity(EntityId("missing"))

    asyncio.run(scenario())
