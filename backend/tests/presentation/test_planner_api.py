"""Tests for the Planner API (ES-018).

Each test builds a fresh app via ``create_app`` and overrides the Planner Service
with one composed from in-memory-backed Investigation/Graph/Memory services. Data is
seeded directly into the in-memory repositories. The tests assert the failure
isolation contract: a valid action whose downstream fails returns HTTP 200 with
``execution_status="failed"``.
"""

import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.application.graph import GraphService
from app.application.investigation import InvestigationService
from app.application.memory import MemoryService
from app.application.planner import PlannerService
from app.domain.entity import Entity
from app.domain.enums import InvestigationStatus, MemoryStatus
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    MemoryItemId,
    RelationshipId,
    ReportId,
)
from app.domain.investigation import Investigation
from app.domain.memory_item import MemoryItem
from app.domain.relationship import Relationship
from app.domain.report import Report
from app.domain.value_objects import (
    ActorRef,
    Confidence,
    EntityType,
    MemoryType,
    Priority,
    RelationshipType,
)
from app.main import create_app
from app.presentation.api.authorization import require_authorization
from app.presentation.api.generation import get_id_generator
from app.presentation.api.v1.planner.dependencies import get_planner_service
from tests.support.doubles import (
    InMemoryOutcomeRepository,
    InMemoryTraceRepository,
)

_NOW = datetime(2026, 6, 30, tzinfo=UTC)


# --------------------------------------------------------------- in-memory doubles


class _InvestigationRepo:
    def __init__(self) -> None:
        self.items: dict[str, Investigation] = {}

    async def add(self, investigation: Investigation) -> None:
        self.items[investigation.id.value] = investigation

    async def get(self, investigation_id: InvestigationId) -> Investigation | None:
        return self.items.get(investigation_id.value)

    async def update(self, investigation: Investigation) -> None:
        self.items[investigation.id.value] = investigation


class _EvidenceRepo:
    async def add(self, evidence: Evidence) -> None: ...
    async def get(self, evidence_id: EvidenceId) -> Evidence | None:
        return None
    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Evidence, ...]:
        return ()


class _FindingRepo:
    async def add(self, finding: Finding) -> None: ...
    async def get(self, finding_id: FindingId) -> Finding | None:
        return None
    async def update(self, finding: Finding) -> None: ...
    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Finding, ...]:
        return ()


class _ReportRepo:
    async def add(self, report: Report) -> None: ...
    async def get(self, report_id: ReportId) -> Report | None:
        return None
    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Report, ...]:
        return ()


class _GraphRepo:
    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.relationships: dict[str, Relationship] = {}

    async def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id.value] = entity

    async def get_entity(self, entity_id: EntityId) -> Entity | None:
        return self.entities.get(entity_id.value)

    async def update_entity(self, entity: Entity) -> None:
        self.entities[entity.id.value] = entity

    async def add_relationship(self, relationship: Relationship) -> None:
        self.relationships[relationship.id.value] = relationship

    async def get_relationship(
        self, relationship_id: RelationshipId
    ) -> Relationship | None:
        return self.relationships.get(relationship_id.value)

    async def update_relationship(self, relationship: Relationship) -> None:
        self.relationships[relationship.id.value] = relationship

    async def list_relationships_for_entity(
        self, entity_id: EntityId
    ) -> tuple[Relationship, ...]:
        return tuple(
            r for r in self.relationships.values()
            if entity_id in (r.source_entity_id, r.target_entity_id)
        )

    async def neighbors(
        self, entity_id: EntityId, depth: int, max_nodes: int
    ) -> tuple[Entity, ...]:
        result: list[Entity] = []
        for rel in self.relationships.values():
            other: EntityId | None = None
            if rel.source_entity_id == entity_id:
                other = rel.target_entity_id
            elif rel.target_entity_id == entity_id:
                other = rel.source_entity_id
            if other is not None and other.value in self.entities:
                result.append(self.entities[other.value])
        return tuple(result)[:max_nodes]


class _MemoryRepo:
    def __init__(self) -> None:
        self.versions: dict[str, list[MemoryItem]] = {}

    async def add(self, memory_item: MemoryItem) -> None:
        self.versions.setdefault(memory_item.id.value, []).append(memory_item)

    async def get(self, memory_id: MemoryItemId) -> MemoryItem | None:
        items = self.versions.get(memory_id.value)
        return max(items, key=lambda i: i.version) if items else None

    async def update(self, memory_item: MemoryItem) -> None:
        self.versions.setdefault(memory_item.id.value, []).append(memory_item)

    async def list_versions(
        self, memory_id: MemoryItemId
    ) -> tuple[MemoryItem, ...]:
        return tuple(self.versions.get(memory_id.value, ()))


class _FixedId:
    def new_id(self) -> str:
        return "act-1"


class _Harness:
    def __init__(self) -> None:
        self.investigations = _InvestigationRepo()
        self.graph = _GraphRepo()
        self.memory = _MemoryRepo()
        self.service = PlannerService(
            InvestigationService(
                self.investigations,
                _EvidenceRepo(),
                _FindingRepo(),
                _ReportRepo(),
                InMemoryOutcomeRepository(),
                InMemoryTraceRepository(),
            ),
            GraphService(self.graph),
            MemoryService(self.memory),
        )

    def client(self) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_planner_service] = lambda: self.service
        app.dependency_overrides[get_id_generator] = lambda: _FixedId()
        app.dependency_overrides[require_authorization] = lambda: None
        return TestClient(app)


def _investigation(status: InvestigationStatus) -> Investigation:
    return Investigation(
        id=InvestigationId("inv-1"),
        title="Phish",
        status=status,
        created_at=_NOW,
        owner=ActorRef("analyst-1"),
        priority=Priority("high"),
    )


def _execute(client: TestClient, payload: dict[str, object]):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/planner/actions", json=payload)


# ------------------------------------------------------------------------ control


def test_control_complete() -> None:
    response = _Harness().client().post(
        "/api/v1/planner/actions", json={"action": "control", "kind": "complete"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_status"] == "completed"
    assert data["value"] == "complete"
    assert data["action_id"] == "act-1"


# ------------------------------------------------------------------ investigation


def test_get_investigation_completed() -> None:
    harness = _Harness()
    asyncio.run(harness.investigations.add(_investigation(InvestigationStatus.ACTIVE)))
    response = _execute(
        harness.client(),
        {"action": "get_investigation", "investigation_id": "inv-1"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_status"] == "completed"
    assert data["target"] == "investigation"
    assert data["value"]["id"] == "inv-1"


def test_get_investigation_missing_is_failed_not_404() -> None:
    response = _execute(
        _Harness().client(),
        {"action": "get_investigation", "investigation_id": "nope"},
    )
    # Failure isolation: HTTP 200 with a failed execution result, not a 404.
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_status"] == "failed"
    assert data["error"]["code"] == "investigation.not_found"
    assert data["value"] is None


def test_change_investigation_status_completed() -> None:
    harness = _Harness()
    asyncio.run(
        harness.investigations.add(_investigation(InvestigationStatus.CREATED))
    )
    response = _execute(
        harness.client(),
        {
            "action": "change_investigation_status",
            "investigation_id": "inv-1",
            "new_status": "active",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_status"] == "completed"
    assert data["value"]["status"] == "active"


# ------------------------------------------------------------------------- graph


def test_find_neighbors_completed() -> None:
    harness = _Harness()
    e1 = Entity(
        id=EntityId("e1"),
        type=EntityType("endpoint"),
        display_name="host-a",
        confidence=Confidence(0.9),
        source="edr",
    )
    e2 = Entity(
        id=EntityId("e2"),
        type=EntityType("endpoint"),
        display_name="host-b",
        confidence=Confidence(0.9),
        source="edr",
    )
    rel = Relationship(
        id=RelationshipId("r1"),
        source_entity_id=EntityId("e1"),
        target_entity_id=EntityId("e2"),
        type=RelationshipType("connects_to"),
        confidence=Confidence(0.7),
        supporting_evidence=(EvidenceId("ev-1"),),
        created_at=_NOW,
    )
    asyncio.run(harness.graph.add_entity(e1))
    asyncio.run(harness.graph.add_entity(e2))
    asyncio.run(harness.graph.add_relationship(rel))
    response = _execute(
        harness.client(),
        {
            "action": "find_neighbors",
            "entity_id": "e1",
            "depth": 1,
            "max_nodes": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_status"] == "completed"
    assert [e["id"] for e in data["value"]] == ["e2"]


def test_find_neighbors_invalid_depth_is_422() -> None:
    response = _execute(
        _Harness().client(),
        {"action": "find_neighbors", "entity_id": "e1", "depth": 0, "max_nodes": 10},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "planner.invalid_action"


# ------------------------------------------------------------------------ memory


def test_get_memory_completed() -> None:
    harness = _Harness()
    item = MemoryItem(
        id=MemoryItemId("m1"),
        type=MemoryType("attack_pattern"),
        source_investigation_id=InvestigationId("inv-1"),
        confidence=Confidence(0.5),
        status=MemoryStatus.CANDIDATE,
        created_at=_NOW,
        version=1,
    )
    asyncio.run(harness.memory.add(item))
    response = _execute(
        harness.client(), {"action": "get_memory", "memory_id": "m1"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_status"] == "completed"
    assert data["value"]["id"] == "m1"


# ----------------------------------------------------------------- not configured


def test_service_not_configured_returns_503() -> None:
    app = create_app()
    app.dependency_overrides[require_authorization] = lambda: None
    client = TestClient(app)
    response = client.post(
        "/api/v1/planner/actions", json={"action": "control", "kind": "complete"}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "api.persistence_not_configured"
