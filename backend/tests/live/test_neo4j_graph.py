"""Live Neo4j tests for the Graph persistence vertical (ES-048).

Opt-in (`pytest -m live_neo4j`): these run against a real Neo4j and verify the
ES-048 exit criteria — deterministic idempotent schema bootstrap, Entity/
Relationship CRUD with reuse-by-identity and endpoint validation, and real
multi-hop ``find_neighbors`` traversal bounded by ``max_nodes``. Exercised
through the Graph Service over the concrete adapter, plus a thin check that the
Graph API is now live (503 gone). Plain functions, ``asyncio.run``.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from neo4j import AsyncDriver

from app.application.graph import GraphService
from app.application.graph.errors import EntityNotFoundError
from app.application.planner import PlannerService
from app.application.planner.actions import FindNeighborsAction
from app.domain.identifiers import EntityId, RelationshipId
from app.domain.value_objects import Confidence
from app.infrastructure.persistence.neo4j.repositories import Neo4jGraphRepository
from app.infrastructure.persistence.neo4j.schema import (
    bootstrap_graph_schema,
    current_version,
    head_version,
)
from app.main import create_app
from app.presentation.api.authorization import require_authorization
from tests.live.neo4j_support import live_driver, prepare_graph
from tests.support.builders import (
    build_entity,
    build_relationship,
    make_investigation_service,
    make_memory_service,
)

pytestmark = pytest.mark.live_neo4j


def _service(driver: AsyncDriver) -> GraphService:
    return GraphService(Neo4jGraphRepository(driver))


# ------------------------------------------------------------------- migration


def test_bootstrap_is_deterministic_and_idempotent() -> None:
    asyncio.run(_bootstrap_scenario())


async def _bootstrap_scenario() -> None:
    driver = live_driver()
    try:
        # Running twice reaches the same head version; the second run is a no-op.
        first = await bootstrap_graph_schema(driver)
        second = await bootstrap_graph_schema(driver)
        assert first == head_version()
        assert second == head_version()
        assert await current_version(driver) == head_version()
    finally:
        await driver.close()


# ---------------------------------------------------------------------- entity


def test_entity_crud_and_reuse_by_identity() -> None:
    asyncio.run(_entity_scenario())


async def _entity_scenario() -> None:
    driver = live_driver()
    try:
        await prepare_graph(driver)
        service = _service(driver)

        created = await service.create_entity(
            build_entity(
                "ent-1", type_value="endpoint", display_name="FIN-WS-12"
            )
        )
        assert created.id == EntityId("ent-1")

        # Reuse-by-identity: a second create with the same id returns the
        # existing entity unchanged (Domain Rule 3).
        reused = await service.create_entity(
            build_entity("ent-1", display_name="DIFFERENT")
        )
        assert reused.display_name == "FIN-WS-12"

        # Round trip preserves every field, incl. attributes (JSON) + aliases.
        entity = build_entity("ent-2", display_name="node-2")
        entity.attributes = {"os": "windows", "role": "workstation"}
        entity.aliases = ("ws-12", "fin-12")
        await service.create_entity(entity)
        loaded = await service.get_entity(EntityId("ent-2"))
        assert loaded.display_name == "node-2"
        assert loaded.attributes == {"os": "windows", "role": "workstation"}
        assert loaded.aliases == ("ws-12", "fin-12")

        # Attribute update touches only the intended field.
        await service.update_entity_attributes(
            EntityId("ent-2"), {"os": "linux"}
        )
        updated = await service.get_entity(EntityId("ent-2"))
        assert updated.attributes == {"os": "linux"}

        # Unknown entities stay observable as a business error, not a crash.
        with pytest.raises(EntityNotFoundError):
            await service.get_entity(EntityId("missing"))
    finally:
        await driver.close()


# ------------------------------------------------------------------ relationship


def test_relationship_crud_and_listing() -> None:
    asyncio.run(_relationship_scenario())


async def _relationship_scenario() -> None:
    driver = live_driver()
    try:
        await prepare_graph(driver)
        service = _service(driver)

        await service.create_entity(build_entity("a"))
        await service.create_entity(build_entity("b"))

        # A relationship to a missing endpoint is rejected (service validation).
        with pytest.raises(EntityNotFoundError):
            await service.create_relationship(
                build_relationship("r-bad", "a", "missing")
            )

        await service.create_relationship(
            build_relationship(
                "r-1", "a", "b", type_value="communicates_with"
            )
        )

        # Round trip preserves type/confidence/evidence/endpoints.
        stored = await service.get_relationship(RelationshipId("r-1"))
        assert stored.source_entity_id == EntityId("a")
        assert stored.target_entity_id == EntityId("b")
        assert stored.type.value == "communicates_with"
        assert [e.value for e in stored.supporting_evidence] == ["ev-1"]

        # Confidence update touches only that field.
        await service.update_relationship_confidence(
            RelationshipId("r-1"), Confidence(0.42)
        )
        reread = await service.get_relationship(RelationshipId("r-1"))
        assert reread.confidence.value == 0.42

        # Listing is incident-edge scoped (both directions).
        incident = await service.list_relationships_for_entity(EntityId("b"))
        assert [r.id.value for r in incident] == ["r-1"]
    finally:
        await driver.close()


# ----------------------------------------------------------------- traversal


def test_find_neighbors_real_traversal() -> None:
    asyncio.run(_traversal_scenario())


async def _traversal_scenario() -> None:
    driver = live_driver()
    try:
        await prepare_graph(driver)
        service = _service(driver)

        # Chain: a - b - c - d
        for entity_id in ("a", "b", "c", "d"):
            await service.create_entity(build_entity(entity_id))
        await service.create_relationship(build_relationship("r-ab", "a", "b"))
        await service.create_relationship(build_relationship("r-bc", "b", "c"))
        await service.create_relationship(build_relationship("r-cd", "c", "d"))

        one_hop = await service.find_neighbors(
            EntityId("a"), depth=1, max_nodes=25
        )
        assert sorted(e.id.value for e in one_hop) == ["b"]

        two_hop = await service.find_neighbors(
            EntityId("a"), depth=2, max_nodes=25
        )
        assert sorted(e.id.value for e in two_hop) == ["b", "c"]

        # max_nodes bounds the result (resource limit only).
        bounded = await service.find_neighbors(
            EntityId("a"), depth=3, max_nodes=1
        )
        assert len(bounded) == 1

        # Traversal on an unknown entity is a business error.
        with pytest.raises(EntityNotFoundError):
            await service.find_neighbors(
                EntityId("missing"), depth=1, max_nodes=5
            )
    finally:
        await driver.close()


# ------------------------------------------------------------- graph API live


async def _prepare_graph_only() -> None:
    # Open and close the driver within one event loop (Windows proactor
    # rejects closing async sockets across event loops).
    driver = live_driver()
    try:
        await prepare_graph(driver)
    finally:
        await driver.close()


def test_graph_api_is_live_against_neo4j() -> None:
    # The Graph API is bound to the real Neo4j adapter (ES-048): 503 gone.
    asyncio.run(_prepare_graph_only())

    app = create_app()
    app.dependency_overrides[require_authorization] = lambda: None
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/graph/entities",
            json={
                "id": "api-ent-1",
                "type": "endpoint",
                "display_name": "host-a",
                "confidence": 0.9,
                "source": "edr",
            },
        )
        assert created.status_code == 201

        fetched = client.get("/api/v1/graph/entities/api-ent-1")
        assert fetched.status_code == 200
        assert fetched.json()["data"]["display_name"] == "host-a"

        # Unknown entity → 404 from the live store (not the old 503 unbound).
        missing = client.get("/api/v1/graph/entities/nope")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "graph.entity_not_found"


def test_planner_find_neighbors_returns_real_neighbours() -> None:
    asyncio.run(_planner_scenario())


async def _planner_scenario() -> None:
    driver = live_driver()
    try:
        await prepare_graph(driver)
        service = _service(driver)
        await service.create_entity(build_entity("p-a"))
        await service.create_entity(build_entity("p-b"))
        await service.create_relationship(
            build_relationship("p-r", "p-a", "p-b")
        )

        # The Planner executes find_neighbors against the real graph and
        # returns real neighbours (no contained failure while Neo4j is up).
        planner = PlannerService(
            make_investigation_service(), service, make_memory_service()
        )
        result = await planner.execute(
            FindNeighborsAction(
                action_id="act-1",
                entity_id=EntityId("p-a"),
                depth=1,
                max_nodes=10,
            )
        )
        assert result.status.value == "completed"
        assert isinstance(result.value, tuple)
        assert [e.id.value for e in result.value] == ["p-b"]
    finally:
        await driver.close()
