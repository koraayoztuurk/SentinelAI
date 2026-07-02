"""Integration tests: Planner orchestration across service boundaries (ES-034).

One application instance binds the Investigation, Graph, Memory and Planner APIs
over the *same* underlying service instances, so a Planner action executed through
``POST /api/v1/planner/actions`` and a resource request through the resource APIs
observe the same state. This verifies the cross-domain collaboration the Planner
Service owns (application-layer orchestration) and the dependency consistency
between the presentation boundaries (integration-testing §5 — collaboration,
dependency and cross-domain validation).
"""

import pytest
from fastapi.testclient import TestClient

from app.application.planner import PlannerService
from app.main import create_app
from app.presentation.api.authorization import require_authorization
from app.presentation.api.generation import get_clock, get_id_generator
from app.presentation.api.v1.graph.dependencies import get_graph_service
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from app.presentation.api.v1.memory.dependencies import get_memory_service
from app.presentation.api.v1.planner.dependencies import get_planner_service
from tests.support.builders import (
    FIXED_TIME,
    make_graph_service,
    make_investigation_service,
    make_memory_service,
)
from tests.support.doubles import FixedClock, SequentialIdGenerator

pytestmark = pytest.mark.integration


def _client() -> TestClient:
    """One app whose resource APIs and Planner API share the same services."""

    investigation = make_investigation_service()
    graph = make_graph_service()
    memory = make_memory_service()
    planner = PlannerService(investigation, graph, memory)
    ids = SequentialIdGenerator()
    clock = FixedClock(FIXED_TIME)

    app = create_app()
    app.dependency_overrides[get_investigation_service] = lambda: investigation
    app.dependency_overrides[get_graph_service] = lambda: graph
    app.dependency_overrides[get_memory_service] = lambda: memory
    app.dependency_overrides[get_planner_service] = lambda: planner
    app.dependency_overrides[get_id_generator] = lambda: ids
    app.dependency_overrides[get_clock] = lambda: clock
    app.dependency_overrides[require_authorization] = lambda: None
    return TestClient(app)


def test_planner_status_change_is_visible_through_resource_api() -> None:
    """A Planner-effected state change is observable through the resource API."""

    client = _client()

    investigation_id = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "analyst-1", "priority": "high"},
    ).json()["data"]["id"]

    executed = client.post(
        "/api/v1/planner/actions",
        json={
            "action": "change_investigation_status",
            "investigation_id": investigation_id,
            "new_status": "active",
        },
    )
    assert executed.status_code == 200
    assert executed.json()["data"]["execution_status"] == "completed"

    fetched = client.get(f"/api/v1/investigations/{investigation_id}")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["status"] == "active"


def test_planner_traverses_graph_created_through_graph_api() -> None:
    """Planner traversal observes entities/relationships created via the Graph API."""

    client = _client()

    for entity_id, name in (("e-1", "host-a"), ("e-2", "host-b")):
        response = client.post(
            "/api/v1/graph/entities",
            json={
                "id": entity_id,
                "type": "endpoint",
                "display_name": name,
                "confidence": 0.9,
                "source": "edr",
            },
        )
        assert response.status_code == 201

    relationship = client.post(
        "/api/v1/graph/relationships",
        json={
            "source_entity_id": "e-1",
            "target_entity_id": "e-2",
            "type": "communicates_with",
            "confidence": 0.8,
            "supporting_evidence": ["ev-1"],
        },
    )
    assert relationship.status_code == 201

    executed = client.post(
        "/api/v1/planner/actions",
        json={
            "action": "find_neighbors",
            "entity_id": "e-1",
            "depth": 1,
            "max_nodes": 10,
        },
    )
    assert executed.status_code == 200
    data = executed.json()["data"]
    assert data["execution_status"] == "completed"
    assert [entity["id"] for entity in data["value"]] == ["e-2"]


def test_planner_reads_memory_created_through_memory_api() -> None:
    """The Planner observes a Memory Item created via the Memory API."""

    client = _client()

    created = client.post(
        "/api/v1/memory",
        json={
            "type": "attack_pattern",
            "source_investigation_id": "inv-1",
            "confidence": 0.9,
            "status": "candidate",
        },
    )
    assert created.status_code == 201
    memory_id = created.json()["data"]["id"]

    executed = client.post(
        "/api/v1/planner/actions",
        json={"action": "get_memory", "memory_id": memory_id},
    )
    assert executed.status_code == 200
    data = executed.json()["data"]
    assert data["execution_status"] == "completed"
    assert data["value"]["id"] == memory_id


def test_same_downstream_error_surfaces_per_boundary_contract() -> None:
    """One downstream failure, two documented interface translations.

    The resource API translates a missing investigation to HTTP 404; the Planner
    API isolates the same failure into HTTP 200 + ``execution_status="failed"``
    (the ES-018 failure-isolation contract). Both boundaries stay consistent with
    their own documented interface over the same shared service state.
    """

    client = _client()

    direct = client.get("/api/v1/investigations/missing")
    assert direct.status_code == 404
    assert direct.json()["error"]["code"] == "investigation.not_found"

    executed = client.post(
        "/api/v1/planner/actions",
        json={"action": "get_investigation", "investigation_id": "missing"},
    )
    assert executed.status_code == 200
    data = executed.json()["data"]
    assert data["execution_status"] == "failed"
    assert data["error"]["code"] == "investigation.not_found"
