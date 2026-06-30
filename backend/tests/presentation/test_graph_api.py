"""Tests for the Graph API (ES-016).

Each test builds a fresh app via ``create_app`` and overrides the service and the
id/clock generators with deterministic in-memory doubles, so real endpoints
(controllers, schemas, envelope and error translation) are exercised end to end
without a database.
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.application.graph import GraphService
from app.domain.entity import Entity
from app.domain.identifiers import EntityId, RelationshipId
from app.domain.relationship import Relationship
from app.main import create_app
from app.presentation.api.authorization import require_authorization
from app.presentation.api.generation import get_clock, get_id_generator
from app.presentation.api.v1.graph.dependencies import get_graph_service

_FIXED_TIME = datetime(2026, 6, 30, tzinfo=UTC)


# --------------------------------------------------------------- in-memory double


class _GraphRepo:
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
            r for r in self._relationships.values()
            if entity_id in (r.source_entity_id, r.target_entity_id)
        )

    async def neighbors(
        self, entity_id: EntityId, depth: int, max_nodes: int
    ) -> tuple[Entity, ...]:
        ids: list[str] = []
        for rel in self._relationships.values():
            if rel.source_entity_id == entity_id:
                ids.append(rel.target_entity_id.value)
            elif rel.target_entity_id == entity_id:
                ids.append(rel.source_entity_id.value)
        seen: dict[str, Entity] = {}
        for value in ids:
            entity = self._entities.get(value)
            if entity is not None:
                seen[value] = entity
        return tuple(seen.values())[:max_nodes]


class _CountingIds:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"rel-{self._n}"


class _FixedClock:
    def now(self) -> datetime:
        return _FIXED_TIME


def _client() -> TestClient:
    app = create_app()
    service = GraphService(_GraphRepo())
    app.dependency_overrides[get_graph_service] = lambda: service
    app.dependency_overrides[get_id_generator] = lambda: _CountingIds()
    app.dependency_overrides[get_clock] = lambda: _FixedClock()
    app.dependency_overrides[require_authorization] = lambda: None
    return TestClient(app)


def _entity_payload(entity_id: str, display_name: str = "host-a") -> dict[str, object]:
    return {
        "id": entity_id,
        "type": "endpoint",
        "display_name": display_name,
        "confidence": 0.9,
        "source": "edr",
    }


def _create_entity(
    client: TestClient, entity_id: str, display_name: str = "host-a"
) -> None:
    response = client.post(
        "/api/v1/graph/entities", json=_entity_payload(entity_id, display_name)
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------- entity


def test_create_entity_envelope() -> None:
    response = _client().post("/api/v1/graph/entities", json=_entity_payload("e1"))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["id"] == "e1"
    assert body["data"]["type"] == "endpoint"
    assert body["meta"]["request_id"] == response.headers.get("X-Request-ID")


def test_get_entity() -> None:
    client = _client()
    _create_entity(client, "e1")
    response = client.get("/api/v1/graph/entities/e1")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == "e1"


def test_get_missing_entity_returns_404() -> None:
    response = _client().get("/api/v1/graph/entities/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "graph.entity_not_found"


def test_create_entity_reuse_returns_existing() -> None:
    client = _client()
    _create_entity(client, "e1", display_name="original")
    second = client.post(
        "/api/v1/graph/entities", json=_entity_payload("e1", display_name="changed")
    )
    assert second.status_code == 201
    # Idempotent reuse: the existing entity is returned unchanged.
    assert second.json()["data"]["display_name"] == "original"


def test_update_entity_attributes() -> None:
    client = _client()
    _create_entity(client, "e1")
    response = client.post(
        "/api/v1/graph/entities/e1/attributes",
        json={"attributes": {"os": "linux"}},
    )
    assert response.status_code == 200
    assert response.json()["data"]["attributes"] == {"os": "linux"}


# ---------------------------------------------------------------- relationship


def _create_relationship(client: TestClient) -> str:
    _create_entity(client, "e1", "host-a")
    _create_entity(client, "e2", "host-b")
    response = client.post(
        "/api/v1/graph/relationships",
        json={
            "source_entity_id": "e1",
            "target_entity_id": "e2",
            "type": "connects_to",
            "confidence": 0.7,
            "supporting_evidence": ["ev-1"],
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_create_relationship_generates_id_and_timestamp() -> None:
    client = _client()
    relationship_id = _create_relationship(client)
    assert relationship_id == "rel-1"
    fetched = client.get(f"/api/v1/graph/relationships/{relationship_id}")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["created_at"].startswith("2026-06-30")


def test_create_relationship_missing_endpoint_returns_404() -> None:
    client = _client()
    _create_entity(client, "e1")
    response = client.post(
        "/api/v1/graph/relationships",
        json={
            "source_entity_id": "e1",
            "target_entity_id": "missing",
            "type": "connects_to",
            "confidence": 0.7,
            "supporting_evidence": ["ev-1"],
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "graph.entity_not_found"


def test_get_missing_relationship_returns_404() -> None:
    response = _client().get("/api/v1/graph/relationships/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "graph.relationship_not_found"


def test_update_relationship_confidence() -> None:
    client = _client()
    relationship_id = _create_relationship(client)
    response = client.post(
        f"/api/v1/graph/relationships/{relationship_id}/confidence",
        json={"confidence": 0.95},
    )
    assert response.status_code == 200
    assert response.json()["data"]["confidence"] == 0.95


def test_list_relationships_for_entity() -> None:
    client = _client()
    relationship_id = _create_relationship(client)
    response = client.get("/api/v1/graph/entities/e1/relationships")
    assert response.status_code == 200
    assert [r["id"] for r in response.json()["data"]] == [relationship_id]


# ------------------------------------------------------------------- traversal


def test_find_neighbors() -> None:
    client = _client()
    _create_relationship(client)
    response = client.get("/api/v1/graph/entities/e1/neighbors?depth=1&max_nodes=10")
    assert response.status_code == 200
    assert [e["id"] for e in response.json()["data"]] == ["e2"]


def test_find_neighbors_invalid_depth_returns_422() -> None:
    client = _client()
    _create_entity(client, "e1")
    response = client.get("/api/v1/graph/entities/e1/neighbors?depth=0&max_nodes=10")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "api.validation_error"


# ----------------------------------------------------------------- not configured


def test_service_not_configured_returns_503() -> None:
    app = create_app()
    app.dependency_overrides[require_authorization] = lambda: None
    client = TestClient(app)
    response = client.post("/api/v1/graph/entities", json=_entity_payload("e1"))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "api.persistence_not_configured"
