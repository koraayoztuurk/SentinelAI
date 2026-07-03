"""Planner API controller.

A single thin controller that executes one Planner Action per request: parse the
discriminated-union action, map it to a domain ``PlannerAction``, delegate to the
Planner Service and wrap its ``ExecutionResult`` in the standard envelope.

The Planner Service isolates downstream failures into a failed ``ExecutionResult``
rather than raising, so a valid action whose downstream fails returns HTTP 200 with
``execution_status="failed"``. Only precondition violations (`InvalidActionError`,
translated to 422) and an unbound service (503) produce HTTP error responses.

Contract status: **transitional, not part of the stable public API** (api-design
§8, ADR-010 Notes). The documented caller of the Planner Service is the AI
Runtime's Investigation Loop; this endpoint exists until that loop has a runtime
invocation surface and will be superseded by an investigation-level execution
surface.
"""

from fastapi import APIRouter, Depends, status

from app.application.planner import PlannerService
from app.presentation.api.context import RequestContext, get_request_context
from app.presentation.api.generation import IdGenerator, get_id_generator
from app.presentation.api.response import ApiResponse, build_success
from app.presentation.api.v1.planner.dependencies import get_planner_service
from app.presentation.api.v1.planner.schemas import (
    PlannerActionRequest,
    PlannerExecutionResponse,
    from_execution_result,
)

planner_router = APIRouter(prefix="/planner", tags=["planner"])


@planner_router.post(
    "/actions",
    response_model=ApiResponse[PlannerExecutionResponse[object]],
    status_code=status.HTTP_200_OK,
)
async def execute_action(
    body: PlannerActionRequest,
    service: PlannerService = Depends(get_planner_service),
    context: RequestContext = Depends(get_request_context),
    ids: IdGenerator = Depends(get_id_generator),
) -> ApiResponse[PlannerExecutionResponse[object]]:
    action = body.to_domain(action_id=ids.new_id())
    result = await service.execute(action)
    return build_success(from_execution_result(result), context)
