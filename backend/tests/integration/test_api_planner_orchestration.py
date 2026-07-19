"""Integration tests: Planner orchestration across service boundaries (ES-034).

The transitional ``POST /api/v1/planner/actions`` resource was removed by
ES-044 (slice decision V-2): the Planner Service is now an application-layer
executor behind the Investigation Loop. These tests therefore drive the
Planner Service directly over the *same* service instances the resource APIs
are bound to, and observe its effects through the HTTP boundaries — verifying
the cross-domain collaboration the Planner Service owns and the per-boundary
error contracts (integration-testing §5).
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.application.planner import PlannerService
from app.application.planner.actions import (
    ChangeInvestigationStatusAction,
    ExecutionResult,
    FindNeighborsAction,
    GetInvestigationAction,
    GetMemoryAction,
    PlannerAction,
)
from app.domain.enums import InvestigationStatus
from app.domain.identifiers import EntityId, InvestigationId, MemoryItemId
from app.domain.memory_item import MemoryItem
from app.main import create_app
from app.presentation.api.authorization import require_authorization
from app.presentation.api.generation import get_clock, get_id_generator
from app.presentation.api.v1.graph.dependencies import get_graph_service
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from app.presentation.api.v1.memory.dependencies import get_memory_service
from tests.support.auth import override_identity
from tests.support.builders import (
    FIXED_TIME,
    make_graph_service,
    make_investigation_service,
    make_memory_service,
)
from tests.support.doubles import FixedClock, SequentialIdGenerator

pytestmark = pytest.mark.integration


class _Stack:
    """One app whose resource APIs and the Planner share the same services."""

    def __init__(self) -> None:
        self.investigation = make_investigation_service()
        self.graph = make_graph_service()
        self.memory = make_memory_service()
        self.planner = PlannerService(
            self.investigation, self.graph, self.memory
        )

        app = create_app()
        app.dependency_overrides[get_investigation_service] = (
            lambda: self.investigation
        )
        app.dependency_overrides[get_graph_service] = lambda: self.graph
        app.dependency_overrides[get_memory_service] = lambda: self.memory
        app.dependency_overrides[get_id_generator] = (
            lambda: SequentialIdGenerator()
        )
        app.dependency_overrides[get_clock] = lambda: FixedClock(FIXED_TIME)
        app.dependency_overrides[require_authorization] = lambda: None
        override_identity(app)
        self.client = TestClient(app)

    def execute(self, action: PlannerAction) -> ExecutionResult:
        return asyncio.run(self.planner.execute(action))


def test_planner_status_change_is_visible_through_resource_api() -> None:
    """A Planner-effected state change is observable through the resource API."""

    stack = _Stack()

    investigation_id = stack.client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "analyst-1", "priority": "high"},
    ).json()["data"]["id"]

    result = stack.execute(
        ChangeInvestigationStatusAction(
            action_id="act-1",
            investigation_id=InvestigationId(investigation_id),
            new_status=InvestigationStatus.ACTIVE,
        )
    )
    assert result.status.value == "completed"

    fetched = stack.client.get(f"/api/v1/investigations/{investigation_id}")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["status"] == "active"


def test_planner_traverses_graph_created_through_graph_api() -> None:
    """Planner traversal observes entities/relationships created via the Graph API."""

    stack = _Stack()

    for entity_id, name in (("e-1", "host-a"), ("e-2", "host-b")):
        response = stack.client.post(
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

    relationship = stack.client.post(
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

    result = stack.execute(
        FindNeighborsAction(
            action_id="act-2",
            entity_id=EntityId("e-1"),
            depth=1,
            max_nodes=10,
        )
    )
    assert result.status.value == "completed"
    value = result.value
    assert isinstance(value, tuple)
    assert [entity.id.value for entity in value] == ["e-2"]


def test_planner_reads_memory_created_through_memory_api() -> None:
    """The Planner observes a Memory Item created via the Memory API."""

    stack = _Stack()

    created = stack.client.post(
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

    result = stack.execute(
        GetMemoryAction(action_id="act-3", memory_id=MemoryItemId(memory_id))
    )
    assert result.status.value == "completed"
    assert isinstance(result.value, MemoryItem)
    assert result.value.id.value == memory_id


def test_same_downstream_error_surfaces_per_boundary_contract() -> None:
    """One downstream failure, two documented interface translations.

    The resource API translates a missing investigation to HTTP 404; the
    Planner Service isolates the same failure into a failed execution result
    (the failure-isolation contract the Investigation Loop observes). Both
    boundaries stay consistent over the same shared service state.
    """

    stack = _Stack()

    direct = stack.client.get("/api/v1/investigations/missing")
    assert direct.status_code == 404
    assert direct.json()["error"]["code"] == "investigation.not_found"

    result = stack.execute(
        GetInvestigationAction(
            action_id="act-4", investigation_id=InvestigationId("missing")
        )
    )
    assert result.status.value == "failed"
    assert result.error is not None
    assert result.error.code == "investigation.not_found"
