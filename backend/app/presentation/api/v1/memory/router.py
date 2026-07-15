"""Memory API controllers.

Thin controllers for the Memory resource. Each follows the same flow: parse the
request, map it to a domain object (in ``schemas``), delegate to the Memory Service
and wrap the result in the standard response envelope. No business logic lives here;
the version-supersede, history and deprecation semantics belong to the service.
"""

from fastapi import APIRouter, Depends, Query, status

from app.application.memory import MemoryService
from app.domain.identifiers import InvestigationId, MemoryItemId
from app.presentation.api.context import RequestContext, get_request_context
from app.presentation.api.generation import (
    Clock,
    IdGenerator,
    get_clock,
    get_id_generator,
)
from app.presentation.api.response import ApiResponse, build_success
from app.presentation.api.v1.memory.dependencies import get_memory_service
from app.presentation.api.v1.memory.schemas import (
    MemoryCreateRequest,
    MemoryItemResponse,
    MemoryUpdateRequest,
)

memory_router = APIRouter(prefix="/memory", tags=["memory"])


@memory_router.post(
    "",
    response_model=ApiResponse[MemoryItemResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_memory(
    body: MemoryCreateRequest,
    service: MemoryService = Depends(get_memory_service),
    context: RequestContext = Depends(get_request_context),
    ids: IdGenerator = Depends(get_id_generator),
    clock: Clock = Depends(get_clock),
) -> ApiResponse[MemoryItemResponse]:
    item = body.to_domain(id_value=ids.new_id(), created_at=clock.now())
    created = await service.create(item)
    return build_success(MemoryItemResponse.from_domain(created), context)


@memory_router.get(
    "",
    response_model=ApiResponse[list[MemoryItemResponse]],
)
async def list_memory(
    investigation_id: str = Query(min_length=1),
    service: MemoryService = Depends(get_memory_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[list[MemoryItemResponse]]:
    """List the latest Memory Item versions originating from an investigation.

    The identifier is a structural cross-service reference
    (database-architecture §8a): an unknown investigation yields an empty
    list, not an error. Memory is the shared knowledge layer (§6a), so the
    listing is open to any authenticated identity.
    """

    items = await service.list_for_investigation(
        InvestigationId(investigation_id)
    )
    return build_success(
        [MemoryItemResponse.from_domain(item) for item in items], context
    )


@memory_router.get(
    "/{memory_id}",
    response_model=ApiResponse[MemoryItemResponse],
)
async def get_memory(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[MemoryItemResponse]:
    item = await service.get(MemoryItemId(memory_id))
    return build_success(MemoryItemResponse.from_domain(item), context)


@memory_router.put(
    "/{memory_id}",
    response_model=ApiResponse[MemoryItemResponse],
)
async def update_memory(
    memory_id: str,
    body: MemoryUpdateRequest,
    service: MemoryService = Depends(get_memory_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[MemoryItemResponse]:
    item = body.to_domain(id_value=memory_id)
    updated = await service.update(item)
    return build_success(MemoryItemResponse.from_domain(updated), context)


@memory_router.post(
    "/{memory_id}/deprecate",
    response_model=ApiResponse[MemoryItemResponse],
)
async def deprecate_memory(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[MemoryItemResponse]:
    item = await service.deprecate(MemoryItemId(memory_id))
    return build_success(MemoryItemResponse.from_domain(item), context)


@memory_router.get(
    "/{memory_id}/history",
    response_model=ApiResponse[list[MemoryItemResponse]],
)
async def get_memory_history(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[list[MemoryItemResponse]]:
    versions = await service.get_history(MemoryItemId(memory_id))
    return build_success(
        [MemoryItemResponse.from_domain(item) for item in versions], context
    )
