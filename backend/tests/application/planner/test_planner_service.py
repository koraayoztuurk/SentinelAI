"""Unit tests for the Planner Service (ES-008).

Plain pytest functions. The Planner Service is exercised over the real
Investigation/Graph/Memory services, each built on compact dict-backed in-memory
repositories. No live database is required.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.application.graph.service import GraphService
from app.application.investigation.service import InvestigationService
from app.application.memory.service import MemoryService
from app.application.planner import (
    ChangeInvestigationStatusAction,
    ControlAction,
    ControlKind,
    CreateEntityAction,
    CreateInvestigationAction,
    CreateMemoryAction,
    CreateRelationshipAction,
    ExecutionStatus,
    FindNeighborsAction,
    GetInvestigationAction,
    GetMemoryAction,
    InvalidActionError,
    PlannerService,
    TargetService,
)
from app.domain.entity import Entity
from app.domain.enums import InvestigationStatus, MemoryStatus
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    InvestigationId,
    MemoryItemId,
    RelationshipId,
)
from app.domain.investigation import Investigation
from app.domain.memory_item import MemoryItem
from app.domain.relationship import Relationship
from app.domain.value_objects import (
    ActorRef,
    Confidence,
    EntityType,
    MemoryType,
    Priority,
    RelationshipType,
)
from tests.support.doubles import (
    InMemoryOutcomeRepository,
    InMemoryTraceRepository,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


# ------------------------------------------------------- compact in-memory repos


class _InvestigationRepo:
    def __init__(self) -> None:
        self._d: dict[str, Investigation] = {}

    async def add(self, x: Investigation) -> None:
        self._d[x.id.value] = x

    async def get(self, i: InvestigationId) -> Investigation | None:
        return self._d.get(i.value)

    async def update(self, x: Investigation) -> None:
        self._d[x.id.value] = x


class _EvidenceRepo:
    async def add(self, x: object) -> None: ...
    async def get(self, i: object) -> None:
        return None

    async def list_for_investigation(self, i: object) -> tuple[object, ...]:
        return ()


class _FindingRepo:
    async def add(self, x: object) -> None: ...
    async def get(self, i: object) -> None:
        return None

    async def update(self, x: object) -> None: ...
    async def list_for_investigation(self, i: object) -> tuple[object, ...]:
        return ()


class _ReportRepo:
    async def add(self, x: object) -> None: ...
    async def get(self, i: object) -> None:
        return None

    async def list_for_investigation(self, i: object) -> tuple[object, ...]:
        return ()


class _GraphRepo:
    def __init__(self) -> None:
        self._e: dict[str, Entity] = {}
        self._r: dict[str, Relationship] = {}

    async def add_entity(self, x: Entity) -> None:
        self._e[x.id.value] = x

    async def get_entity(self, i: EntityId) -> Entity | None:
        return self._e.get(i.value)

    async def update_entity(self, x: Entity) -> None:
        self._e[x.id.value] = x

    async def add_relationship(self, x: Relationship) -> None:
        self._r[x.id.value] = x

    async def get_relationship(self, i: RelationshipId) -> Relationship | None:
        return self._r.get(i.value)

    async def update_relationship(self, x: Relationship) -> None:
        self._r[x.id.value] = x

    async def list_relationships_for_entity(
        self, i: EntityId
    ) -> tuple[Relationship, ...]:
        return tuple(
            r
            for r in self._r.values()
            if i in (r.source_entity_id, r.target_entity_id)
        )

    async def neighbors(
        self, i: EntityId, depth: int, max_nodes: int
    ) -> tuple[Entity, ...]:
        result: list[Entity] = []
        for r in self._r.values():
            neighbor: EntityId | None = None
            if r.source_entity_id == i:
                neighbor = r.target_entity_id
            elif r.target_entity_id == i:
                neighbor = r.source_entity_id
            if neighbor is not None and neighbor.value in self._e:
                result.append(self._e[neighbor.value])
            if len(result) >= max_nodes:
                break
        return tuple(result)


class _MemoryRepo:
    def __init__(self) -> None:
        self._v: dict[str, list[MemoryItem]] = {}

    async def add(self, x: MemoryItem) -> None:
        self._v.setdefault(x.id.value, []).append(x)

    async def get(self, i: MemoryItemId) -> MemoryItem | None:
        versions = self._v.get(i.value)
        return max(versions, key=lambda m: m.version) if versions else None

    async def update(self, x: MemoryItem) -> None: ...
    async def list_versions(self, i: MemoryItemId) -> tuple[MemoryItem, ...]:
        return tuple(self._v.get(i.value, ()))


def _planner() -> PlannerService:
    investigation = InvestigationService(
        _InvestigationRepo(),
        _EvidenceRepo(),
        _FindingRepo(),
        _ReportRepo(),
        InMemoryOutcomeRepository(),
        InMemoryTraceRepository(),
    )
    graph = GraphService(_GraphRepo())
    memory = MemoryService(_MemoryRepo())
    return PlannerService(investigation, graph, memory)


# ------------------------------------------------------------------------ builders


def _investigation(
    investigation_id: str,
    status: InvestigationStatus = InvestigationStatus.CREATED,
) -> Investigation:
    return Investigation(
        id=InvestigationId(investigation_id),
        title="Test investigation",
        status=status,
        created_at=_NOW,
        owner=ActorRef("analyst-1"),
        priority=Priority("high"),
    )


def _entity(entity_id: str) -> Entity:
    return Entity(
        id=EntityId(entity_id),
        type=EntityType("endpoint"),
        display_name="node",
        confidence=Confidence(0.9),
        source="edr",
    )


def _relationship(relationship_id: str, source: str, target: str) -> Relationship:
    return Relationship(
        id=RelationshipId(relationship_id),
        source_entity_id=EntityId(source),
        target_entity_id=EntityId(target),
        type=RelationshipType("communicates_with"),
        confidence=Confidence(0.8),
        supporting_evidence=(EvidenceId("ev-1"),),
        created_at=_NOW,
    )


def _memory(memory_id: str) -> MemoryItem:
    return MemoryItem(
        id=MemoryItemId(memory_id),
        type=MemoryType("attack_pattern"),
        source_investigation_id=InvestigationId("inv-1"),
        confidence=Confidence(0.9),
        status=MemoryStatus.CANDIDATE,
        created_at=_NOW,
    )


# --------------------------------------------------------------------------- tests


def test_create_investigation_action_completes() -> None:
    async def scenario() -> None:
        planner = _planner()
        result = await planner.execute(
            CreateInvestigationAction("a-1", _investigation("inv-1"))
        )
        assert result.status is ExecutionStatus.COMPLETED
        assert result.target is TargetService.INVESTIGATION
        assert isinstance(result.value, Investigation)
        assert result.error is None

    asyncio.run(scenario())


def test_get_unknown_investigation_action_is_failed() -> None:
    async def scenario() -> None:
        planner = _planner()
        result = await planner.execute(
            GetInvestigationAction("a-1", InvestigationId("missing"))
        )
        assert result.status is ExecutionStatus.FAILED
        assert result.target is TargetService.INVESTIGATION
        assert result.error is not None
        assert result.error.code == "investigation.not_found"

    asyncio.run(scenario())


def test_change_status_action_completes() -> None:
    async def scenario() -> None:
        planner = _planner()
        await planner.execute(CreateInvestigationAction("a-1", _investigation("inv-1")))
        result = await planner.execute(
            ChangeInvestigationStatusAction(
                "a-2", InvestigationId("inv-1"), InvestigationStatus.ACTIVE
            )
        )
        assert result.status is ExecutionStatus.COMPLETED
        assert isinstance(result.value, Investigation)
        assert result.value.status is InvestigationStatus.ACTIVE

    asyncio.run(scenario())


def test_create_entity_action_completes() -> None:
    async def scenario() -> None:
        planner = _planner()
        result = await planner.execute(CreateEntityAction("a-1", _entity("e-1")))
        assert result.status is ExecutionStatus.COMPLETED
        assert result.target is TargetService.GRAPH
        assert isinstance(result.value, Entity)

    asyncio.run(scenario())


def test_create_relationship_missing_endpoints_is_failed() -> None:
    async def scenario() -> None:
        planner = _planner()
        result = await planner.execute(
            CreateRelationshipAction("a-1", _relationship("r-1", "e-1", "e-2"))
        )
        assert result.status is ExecutionStatus.FAILED
        assert result.target is TargetService.GRAPH
        assert result.error is not None
        assert result.error.code == "graph.entity_not_found"

    asyncio.run(scenario())


def test_find_neighbors_action_completes() -> None:
    async def scenario() -> None:
        planner = _planner()
        await planner.execute(CreateEntityAction("a-1", _entity("e-1")))
        await planner.execute(CreateEntityAction("a-2", _entity("e-2")))
        await planner.execute(
            CreateRelationshipAction("a-3", _relationship("r-1", "e-1", "e-2"))
        )
        result = await planner.execute(
            FindNeighborsAction("a-4", EntityId("e-1"), depth=1, max_nodes=10)
        )
        assert result.status is ExecutionStatus.COMPLETED
        assert result.target is TargetService.GRAPH
        assert isinstance(result.value, tuple)
        assert {e.id.value for e in result.value} == {"e-2"}

    asyncio.run(scenario())


def test_create_memory_action_completes() -> None:
    async def scenario() -> None:
        planner = _planner()
        result = await planner.execute(CreateMemoryAction("a-1", _memory("m-1")))
        assert result.status is ExecutionStatus.COMPLETED
        assert result.target is TargetService.MEMORY
        assert isinstance(result.value, MemoryItem)

    asyncio.run(scenario())


def test_get_unknown_memory_action_is_failed() -> None:
    async def scenario() -> None:
        planner = _planner()
        result = await planner.execute(
            GetMemoryAction("a-1", MemoryItemId("missing"))
        )
        assert result.status is ExecutionStatus.FAILED
        assert result.target is TargetService.MEMORY
        assert result.error is not None
        assert result.error.code == "memory.not_found"

    asyncio.run(scenario())


def test_control_action_completes_with_no_target() -> None:
    async def scenario() -> None:
        planner = _planner()
        result = await planner.execute(ControlAction("a-1", ControlKind.COMPLETE))
        assert result.status is ExecutionStatus.COMPLETED
        assert result.target is None
        assert result.value is ControlKind.COMPLETE

    asyncio.run(scenario())


def test_blank_action_id_raises() -> None:
    async def scenario() -> None:
        planner = _planner()
        with pytest.raises(InvalidActionError):
            await planner.execute(ControlAction("  ", ControlKind.ESCALATE))

    asyncio.run(scenario())


def test_non_positive_traversal_limits_raise() -> None:
    async def scenario() -> None:
        planner = _planner()
        with pytest.raises(InvalidActionError):
            await planner.execute(
                FindNeighborsAction("a-1", EntityId("e-1"), depth=0, max_nodes=5)
            )

    asyncio.run(scenario())
