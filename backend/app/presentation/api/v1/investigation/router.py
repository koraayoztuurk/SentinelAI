"""Investigation API controllers.

Thin controllers for the Investigation resource family (investigation, evidence,
finding, report). Each follows the same flow: parse the request, map it to a domain
object (in ``schemas``), delegate to the Investigation Service and wrap the result
in the standard response envelope. No business logic lives here.
"""

from fastapi import APIRouter, Depends, status

from app.application.investigation import (
    EvidenceNotFoundError,
    InvestigationService,
    ReportNotFoundError,
)
from app.domain.identifiers import EvidenceId, InvestigationId, ReportId
from app.presentation.api.context import RequestContext, get_request_context
from app.presentation.api.generation import (
    Clock,
    IdGenerator,
    get_clock,
    get_id_generator,
)
from app.presentation.api.response import ApiResponse, build_success
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from app.presentation.api.v1.investigation.schemas import (
    EvidenceCreateRequest,
    EvidenceResponse,
    FindingCreateRequest,
    FindingResponse,
    FindingUpdateRequest,
    InvestigationCreateRequest,
    InvestigationResponse,
    InvestigationStatusChangeRequest,
    ReportCreateRequest,
    ReportResponse,
)

investigation_router = APIRouter(tags=["investigation"])

# ----------------------------------------------------------------- investigation


@investigation_router.post(
    "/investigations",
    response_model=ApiResponse[InvestigationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_investigation(
    body: InvestigationCreateRequest,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
    ids: IdGenerator = Depends(get_id_generator),
    clock: Clock = Depends(get_clock),
) -> ApiResponse[InvestigationResponse]:
    investigation = body.to_domain(id_value=ids.new_id(), created_at=clock.now())
    created = await service.create(investigation)
    return build_success(InvestigationResponse.from_domain(created), context)


@investigation_router.get(
    "/investigations/{investigation_id}",
    response_model=ApiResponse[InvestigationResponse],
)
async def get_investigation(
    investigation_id: str,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[InvestigationResponse]:
    investigation = await service.get(InvestigationId(investigation_id))
    return build_success(InvestigationResponse.from_domain(investigation), context)


@investigation_router.post(
    "/investigations/{investigation_id}/status",
    response_model=ApiResponse[InvestigationResponse],
)
async def change_investigation_status(
    investigation_id: str,
    body: InvestigationStatusChangeRequest,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[InvestigationResponse]:
    investigation = await service.change_status(
        InvestigationId(investigation_id), body.status
    )
    return build_success(InvestigationResponse.from_domain(investigation), context)


# -------------------------------------------------------------------- evidence


@investigation_router.post(
    "/investigations/{investigation_id}/evidence",
    response_model=ApiResponse[EvidenceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def attach_evidence(
    investigation_id: str,
    body: EvidenceCreateRequest,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
    ids: IdGenerator = Depends(get_id_generator),
    clock: Clock = Depends(get_clock),
) -> ApiResponse[EvidenceResponse]:
    evidence = body.to_domain(
        id_value=ids.new_id(),
        investigation_id_value=investigation_id,
        timestamp=clock.now(),
    )
    attached = await service.attach_evidence(evidence)
    return build_success(EvidenceResponse.from_domain(attached), context)


@investigation_router.get(
    "/investigations/{investigation_id}/evidence",
    response_model=ApiResponse[list[EvidenceResponse]],
)
async def list_evidence(
    investigation_id: str,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[list[EvidenceResponse]]:
    items = await service.list_evidence(InvestigationId(investigation_id))
    return build_success(
        [EvidenceResponse.from_domain(item) for item in items], context
    )


@investigation_router.get(
    "/investigations/{investigation_id}/evidence/{evidence_id}",
    response_model=ApiResponse[EvidenceResponse],
)
async def get_evidence(
    investigation_id: str,
    evidence_id: str,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[EvidenceResponse]:
    evidence = await service.get_evidence(EvidenceId(evidence_id))
    if evidence.investigation_id != InvestigationId(investigation_id):
        raise EvidenceNotFoundError(f"Evidence '{evidence_id}' not found.")
    return build_success(EvidenceResponse.from_domain(evidence), context)


# --------------------------------------------------------------------- finding


@investigation_router.post(
    "/investigations/{investigation_id}/findings",
    response_model=ApiResponse[FindingResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_finding(
    investigation_id: str,
    body: FindingCreateRequest,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
    ids: IdGenerator = Depends(get_id_generator),
    clock: Clock = Depends(get_clock),
) -> ApiResponse[FindingResponse]:
    finding = body.to_domain(
        id_value=ids.new_id(),
        investigation_id_value=investigation_id,
        created_at=clock.now(),
    )
    created = await service.create_finding(finding)
    return build_success(FindingResponse.from_domain(created), context)


@investigation_router.put(
    "/investigations/{investigation_id}/findings/{finding_id}",
    response_model=ApiResponse[FindingResponse],
)
async def update_finding(
    investigation_id: str,
    finding_id: str,
    body: FindingUpdateRequest,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[FindingResponse]:
    finding = body.to_domain(
        id_value=finding_id, investigation_id_value=investigation_id
    )
    updated = await service.update_finding(finding)
    return build_success(FindingResponse.from_domain(updated), context)


@investigation_router.get(
    "/investigations/{investigation_id}/findings",
    response_model=ApiResponse[list[FindingResponse]],
)
async def list_findings(
    investigation_id: str,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[list[FindingResponse]]:
    items = await service.list_findings(InvestigationId(investigation_id))
    return build_success(
        [FindingResponse.from_domain(item) for item in items], context
    )


# ---------------------------------------------------------------------- report


@investigation_router.post(
    "/investigations/{investigation_id}/reports",
    response_model=ApiResponse[ReportResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    investigation_id: str,
    body: ReportCreateRequest,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
    ids: IdGenerator = Depends(get_id_generator),
    clock: Clock = Depends(get_clock),
) -> ApiResponse[ReportResponse]:
    report = body.to_domain(
        id_value=ids.new_id(),
        investigation_id_value=investigation_id,
        created_at=clock.now(),
    )
    created = await service.create_report(report)
    return build_success(ReportResponse.from_domain(created), context)


@investigation_router.get(
    "/investigations/{investigation_id}/reports",
    response_model=ApiResponse[list[ReportResponse]],
)
async def list_reports(
    investigation_id: str,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[list[ReportResponse]]:
    items = await service.list_reports(InvestigationId(investigation_id))
    return build_success(
        [ReportResponse.from_domain(item) for item in items], context
    )


@investigation_router.get(
    "/investigations/{investigation_id}/reports/{report_id}",
    response_model=ApiResponse[ReportResponse],
)
async def get_report(
    investigation_id: str,
    report_id: str,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[ReportResponse]:
    report = await service.get_report(ReportId(report_id))
    if report.investigation_id != InvestigationId(investigation_id):
        raise ReportNotFoundError(f"Report '{report_id}' not found.")
    return build_success(ReportResponse.from_domain(report), context)
