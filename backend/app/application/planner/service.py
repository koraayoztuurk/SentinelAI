"""Planner Service.

The stateless orchestration layer that executes a single Planner Action per
request by dispatching to the Investigation, Graph or Memory service and
returning a provenance-bearing execution result (planner-service.md).

It owns no data, holds no repository and persists no state. Multi-step, adaptive
investigation is the Planner Agent's iterative decision loop, not this service.
Downstream service failures are isolated into a failed execution result rather
than propagated. Logging here is operational observability, not an audit record.
"""

import logging
from typing import assert_never

from app.application.graph.service import GraphService
from app.application.investigation.service import InvestigationService
from app.application.memory.service import MemoryService
from app.application.planner.actions import (
    ChangeInvestigationStatusAction,
    ControlAction,
    CreateEntityAction,
    CreateInvestigationAction,
    CreateMemoryAction,
    CreateRelationshipAction,
    ExecutionError,
    ExecutionResult,
    ExecutionStatus,
    FindNeighborsAction,
    GetInvestigationAction,
    GetMemoryAction,
    PlannerAction,
    ServiceInvocationAction,
    TargetService,
)
from app.application.planner.errors import InvalidActionError
from app.shared.exceptions import SentinelAIError

logger = logging.getLogger(__name__)


class PlannerService:
    """Executes one Planner Action per request by dispatching to a backend service."""

    def __init__(
        self,
        investigation: InvestigationService,
        graph: GraphService,
        memory: MemoryService,
    ) -> None:
        self._investigation = investigation
        self._graph = graph
        self._memory = memory

    async def execute(self, action: PlannerAction) -> ExecutionResult:
        """Validate and execute a single Planner Action, returning its result."""

        self._validate(action)

        if isinstance(action, ControlAction):
            logger.info(
                "planner control action_id=%s kind=%s",
                action.action_id,
                action.kind.value,
            )
            return ExecutionResult(
                action_id=action.action_id,
                target=None,
                status=ExecutionStatus.COMPLETED,
                value=action.kind,
            )

        target = self._target_of(action)
        try:
            value = await self._dispatch(action)
        except SentinelAIError as exc:
            logger.info(
                "planner action failed action_id=%s target=%s code=%s",
                action.action_id,
                target.value,
                exc.code,
            )
            return ExecutionResult(
                action_id=action.action_id,
                target=target,
                status=ExecutionStatus.FAILED,
                error=ExecutionError(code=exc.code, message=exc.message),
            )

        logger.info(
            "planner action executed action_id=%s target=%s status=completed",
            action.action_id,
            target.value,
        )
        return ExecutionResult(
            action_id=action.action_id,
            target=target,
            status=ExecutionStatus.COMPLETED,
            value=value,
        )

    def _validate(self, action: PlannerAction) -> None:
        if not action.action_id.strip():
            raise InvalidActionError("Planner Action must have a non-blank action_id.")
        if isinstance(action, FindNeighborsAction) and (
            action.depth < 1 or action.max_nodes < 1
        ):
            raise InvalidActionError(
                "Traversal limits (depth, max_nodes) must be positive."
            )

    def _target_of(self, action: ServiceInvocationAction) -> TargetService:
        match action:
            case (
                CreateInvestigationAction()
                | GetInvestigationAction()
                | ChangeInvestigationStatusAction()
            ):
                return TargetService.INVESTIGATION
            case (
                CreateEntityAction()
                | CreateRelationshipAction()
                | FindNeighborsAction()
            ):
                return TargetService.GRAPH
            case CreateMemoryAction() | GetMemoryAction():
                return TargetService.MEMORY
            case _:
                assert_never(action)

    async def _dispatch(self, action: ServiceInvocationAction) -> object:
        match action:
            case CreateInvestigationAction():
                return await self._investigation.create(action.investigation)
            case GetInvestigationAction():
                return await self._investigation.get(action.investigation_id)
            case ChangeInvestigationStatusAction():
                return await self._investigation.change_status(
                    action.investigation_id, action.new_status
                )
            case CreateEntityAction():
                return await self._graph.create_entity(action.entity)
            case CreateRelationshipAction():
                return await self._graph.create_relationship(action.relationship)
            case FindNeighborsAction():
                return await self._graph.find_neighbors(
                    action.entity_id, depth=action.depth, max_nodes=action.max_nodes
                )
            case CreateMemoryAction():
                return await self._memory.create(action.memory_item)
            case GetMemoryAction():
                return await self._memory.get(action.memory_id)
            case _:
                assert_never(action)
