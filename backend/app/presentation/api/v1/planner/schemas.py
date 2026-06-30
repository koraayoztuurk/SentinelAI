"""Planner API request/response schemas and mappers.

The request is a discriminated union over the representative Planner Action
vocabulary (control + identifier-based actions); the embedded-domain-object
``Create*`` actions are deferred. Each variant maps to a typed ``PlannerAction``
via ``to_domain``; the controller supplies the API-generated ``action_id``.

The response projects the service's ``ExecutionResult`` into a generic envelope.
``PlannerExecutionResponse[T]`` keeps ``value`` open to the type system (future
callers may parametrize it precisely) while the single polymorphic endpoint uses
``PlannerExecutionResponse[object]`` — Pydantic serializes the projected resource
models by duck typing. Downstream failures are carried as data
(``execution_status``/``error``), never raised, mirroring the Planner Service's
failure-isolation contract.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.application.planner import (
    ChangeInvestigationStatusAction,
    ControlAction,
    ControlKind,
    ExecutionResult,
    FindNeighborsAction,
    GetInvestigationAction,
    GetMemoryAction,
    PlannerAction,
)
from app.domain.entity import Entity
from app.domain.enums import InvestigationStatus
from app.domain.identifiers import EntityId, InvestigationId, MemoryItemId
from app.domain.investigation import Investigation
from app.domain.memory_item import MemoryItem
from app.presentation.api.v1.graph.schemas import EntityResponse
from app.presentation.api.v1.investigation.schemas import InvestigationResponse
from app.presentation.api.v1.memory.schemas import MemoryItemResponse

# ------------------------------------------------------------- action requests


class ControlActionRequest(BaseModel):
    """Execute a control decision (complete / escalate)."""

    action: Literal["control"]
    kind: ControlKind

    def to_domain(self, *, action_id: str) -> PlannerAction:
        return ControlAction(action_id=action_id, kind=self.kind)


class GetInvestigationActionRequest(BaseModel):
    """Retrieve an investigation through the Planner."""

    action: Literal["get_investigation"]
    investigation_id: str

    def to_domain(self, *, action_id: str) -> PlannerAction:
        return GetInvestigationAction(
            action_id=action_id,
            investigation_id=InvestigationId(self.investigation_id),
        )


class ChangeInvestigationStatusActionRequest(BaseModel):
    """Transition an investigation's lifecycle status through the Planner."""

    action: Literal["change_investigation_status"]
    investigation_id: str
    new_status: InvestigationStatus

    def to_domain(self, *, action_id: str) -> PlannerAction:
        return ChangeInvestigationStatusAction(
            action_id=action_id,
            investigation_id=InvestigationId(self.investigation_id),
            new_status=self.new_status,
        )


class FindNeighborsActionRequest(BaseModel):
    """Retrieve neighbouring entities through the Planner."""

    action: Literal["find_neighbors"]
    entity_id: str
    depth: int
    max_nodes: int

    def to_domain(self, *, action_id: str) -> PlannerAction:
        return FindNeighborsAction(
            action_id=action_id,
            entity_id=EntityId(self.entity_id),
            depth=self.depth,
            max_nodes=self.max_nodes,
        )


class GetMemoryActionRequest(BaseModel):
    """Retrieve a Memory Item through the Planner."""

    action: Literal["get_memory"]
    memory_id: str

    def to_domain(self, *, action_id: str) -> PlannerAction:
        return GetMemoryAction(
            action_id=action_id, memory_id=MemoryItemId(self.memory_id)
        )


PlannerActionRequest = Annotated[
    ControlActionRequest
    | GetInvestigationActionRequest
    | ChangeInvestigationStatusActionRequest
    | FindNeighborsActionRequest
    | GetMemoryActionRequest,
    Field(discriminator="action"),
]


# ---------------------------------------------------------------- execution result


class ExecutionErrorBody(BaseModel):
    """A failed action's structured error."""

    code: str
    message: str


class PlannerExecutionResponse[T](BaseModel):
    """Projection of a single Planner Action execution result."""

    action_id: str
    target: str | None
    execution_status: str
    value: T | None = None
    error: ExecutionErrorBody | None = None


def _project_value(value: object) -> object | None:
    if isinstance(value, Investigation):
        return InvestigationResponse.from_domain(value)
    if isinstance(value, MemoryItem):
        return MemoryItemResponse.from_domain(value)
    if isinstance(value, ControlKind):
        return value.value
    if isinstance(value, tuple):
        return [
            EntityResponse.from_domain(item)
            for item in value
            if isinstance(item, Entity)
        ]
    return None


def from_execution_result(
    result: ExecutionResult,
) -> PlannerExecutionResponse[object]:
    """Project an ``ExecutionResult`` into the response envelope."""

    error = (
        ExecutionErrorBody(code=result.error.code, message=result.error.message)
        if result.error is not None
        else None
    )
    return PlannerExecutionResponse[object](
        action_id=result.action_id,
        target=result.target.value if result.target is not None else None,
        execution_status=result.status.value,
        value=_project_value(result.value),
        error=error,
    )
