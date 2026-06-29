"""Planner Action and execution-result contract.

These are transient, application-layer orchestration structures (not domain
objects, per domain-model.md). A Planner Action is the single unit the Planner
Service executes per request (planner-service.md Control Model): either a
service-invocation action targeting one backend service operation, or a control
action that signals the Planner Agent's decision loop.

This task implements a representative set of service-invocation actions; the full
operation catalogue is introduced once the Planner Agent (ES-011) defines its
action vocabulary.
"""

from dataclasses import dataclass
from enum import Enum

from app.domain.entity import Entity
from app.domain.enums import InvestigationStatus
from app.domain.identifiers import EntityId, InvestigationId, MemoryItemId
from app.domain.investigation import Investigation
from app.domain.memory_item import MemoryItem
from app.domain.relationship import Relationship


class TargetService(Enum):
    """The backend service a service-invocation action targets."""

    INVESTIGATION = "investigation"
    GRAPH = "graph"
    MEMORY = "memory"


class ControlKind(Enum):
    """A control decision that signals the Planner Agent's loop (no service call)."""

    COMPLETE = "complete"
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class CreateInvestigationAction:
    """Create an investigation via the Investigation Service."""

    action_id: str
    investigation: Investigation


@dataclass(frozen=True, slots=True)
class GetInvestigationAction:
    """Retrieve an investigation via the Investigation Service."""

    action_id: str
    investigation_id: InvestigationId


@dataclass(frozen=True, slots=True)
class ChangeInvestigationStatusAction:
    """Transition an investigation's lifecycle status via the Investigation Service."""

    action_id: str
    investigation_id: InvestigationId
    new_status: InvestigationStatus


@dataclass(frozen=True, slots=True)
class CreateEntityAction:
    """Create (or reuse) a graph entity via the Graph Service."""

    action_id: str
    entity: Entity


@dataclass(frozen=True, slots=True)
class CreateRelationshipAction:
    """Create a graph relationship via the Graph Service."""

    action_id: str
    relationship: Relationship


@dataclass(frozen=True, slots=True)
class FindNeighborsAction:
    """Retrieve neighbouring entities via the Graph Service."""

    action_id: str
    entity_id: EntityId
    depth: int
    max_nodes: int


@dataclass(frozen=True, slots=True)
class CreateMemoryAction:
    """Create a Memory Item via the Memory Service."""

    action_id: str
    memory_item: MemoryItem


@dataclass(frozen=True, slots=True)
class GetMemoryAction:
    """Retrieve a Memory Item via the Memory Service."""

    action_id: str
    memory_id: MemoryItemId


@dataclass(frozen=True, slots=True)
class ControlAction:
    """A control decision (complete / escalate); performs no service call."""

    action_id: str
    kind: ControlKind


ServiceInvocationAction = (
    CreateInvestigationAction
    | GetInvestigationAction
    | ChangeInvestigationStatusAction
    | CreateEntityAction
    | CreateRelationshipAction
    | FindNeighborsAction
    | CreateMemoryAction
    | GetMemoryAction
)

PlannerAction = ServiceInvocationAction | ControlAction


class ExecutionStatus(Enum):
    """Outcome status of executing a single Planner Action."""

    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ExecutionError:
    """A structured error surfaced when a dispatched action fails."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """The result of executing one Planner Action.

    ``target`` preserves the originating backend service (``None`` for control
    actions); ``value`` holds that service's response on success.
    """

    action_id: str
    target: TargetService | None
    status: ExecutionStatus
    value: object | None = None
    error: ExecutionError | None = None
