"""Graph API controllers.

Thin controllers for the Graph resource family (entities, relationships,
neighbourhood traversal). Each follows the same flow: parse the request, map it to
a domain object (in ``schemas``), delegate to the Graph Service and wrap the result
in the standard response envelope. No business logic lives here.
"""

from fastapi import APIRouter, Depends, Query, status

from app.application.graph import GraphService
from app.domain.identifiers import EntityId, RelationshipId
from app.presentation.api.context import RequestContext, get_request_context
from app.presentation.api.generation import (
    Clock,
    IdGenerator,
    get_clock,
    get_id_generator,
)
from app.presentation.api.response import ApiResponse, build_success
from app.presentation.api.v1.graph.dependencies import get_graph_service
from app.presentation.api.v1.graph.schemas import (
    EntityAttributesUpdateRequest,
    EntityCreateRequest,
    EntityResponse,
    RelationshipConfidenceUpdateRequest,
    RelationshipCreateRequest,
    RelationshipResponse,
)

graph_router = APIRouter(prefix="/graph", tags=["graph"])

# ---------------------------------------------------------------------- entity


@graph_router.post(
    "/entities",
    response_model=ApiResponse[EntityResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_entity(
    body: EntityCreateRequest,
    service: GraphService = Depends(get_graph_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[EntityResponse]:
    entity = await service.create_entity(body.to_domain())
    return build_success(EntityResponse.from_domain(entity), context)


@graph_router.get(
    "/entities/{entity_id}",
    response_model=ApiResponse[EntityResponse],
)
async def get_entity(
    entity_id: str,
    service: GraphService = Depends(get_graph_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[EntityResponse]:
    entity = await service.get_entity(EntityId(entity_id))
    return build_success(EntityResponse.from_domain(entity), context)


@graph_router.post(
    "/entities/{entity_id}/attributes",
    response_model=ApiResponse[EntityResponse],
)
async def update_entity_attributes(
    entity_id: str,
    body: EntityAttributesUpdateRequest,
    service: GraphService = Depends(get_graph_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[EntityResponse]:
    entity = await service.update_entity_attributes(
        EntityId(entity_id), body.attributes
    )
    return build_success(EntityResponse.from_domain(entity), context)


@graph_router.get(
    "/entities/{entity_id}/relationships",
    response_model=ApiResponse[list[RelationshipResponse]],
)
async def list_relationships_for_entity(
    entity_id: str,
    service: GraphService = Depends(get_graph_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[list[RelationshipResponse]]:
    items = await service.list_relationships_for_entity(EntityId(entity_id))
    return build_success(
        [RelationshipResponse.from_domain(item) for item in items], context
    )


@graph_router.get(
    "/entities/{entity_id}/neighbors",
    response_model=ApiResponse[list[EntityResponse]],
)
async def find_neighbors(
    entity_id: str,
    depth: int = Query(ge=1),
    max_nodes: int = Query(ge=1),
    service: GraphService = Depends(get_graph_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[list[EntityResponse]]:
    neighbors = await service.find_neighbors(
        EntityId(entity_id), depth=depth, max_nodes=max_nodes
    )
    return build_success(
        [EntityResponse.from_domain(item) for item in neighbors], context
    )


# ---------------------------------------------------------------- relationship


@graph_router.post(
    "/relationships",
    response_model=ApiResponse[RelationshipResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    body: RelationshipCreateRequest,
    service: GraphService = Depends(get_graph_service),
    context: RequestContext = Depends(get_request_context),
    ids: IdGenerator = Depends(get_id_generator),
    clock: Clock = Depends(get_clock),
) -> ApiResponse[RelationshipResponse]:
    relationship = body.to_domain(id_value=ids.new_id(), created_at=clock.now())
    created = await service.create_relationship(relationship)
    return build_success(RelationshipResponse.from_domain(created), context)


@graph_router.get(
    "/relationships/{relationship_id}",
    response_model=ApiResponse[RelationshipResponse],
)
async def get_relationship(
    relationship_id: str,
    service: GraphService = Depends(get_graph_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[RelationshipResponse]:
    relationship = await service.get_relationship(RelationshipId(relationship_id))
    return build_success(RelationshipResponse.from_domain(relationship), context)


@graph_router.post(
    "/relationships/{relationship_id}/confidence",
    response_model=ApiResponse[RelationshipResponse],
)
async def update_relationship_confidence(
    relationship_id: str,
    body: RelationshipConfidenceUpdateRequest,
    service: GraphService = Depends(get_graph_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[RelationshipResponse]:
    relationship = await service.update_relationship_confidence(
        RelationshipId(relationship_id), body.to_confidence()
    )
    return build_success(RelationshipResponse.from_domain(relationship), context)
