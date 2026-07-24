"""Investigation API controllers.

Thin controllers for the Investigation resource family (investigation, evidence,
finding, report). Each follows the same flow: parse the request, map it to a domain
object (in ``schemas``), delegate to the Investigation Service and wrap the result
in the standard response envelope. No business logic lives here.
"""

import re

from fastapi import APIRouter, Depends, Request, Response, status

from app.ai.orchestration.runner import InvestigationRunner
from app.application.investigation import (
    EvidenceNotFoundError,
    InvestigationService,
    ReportNotFoundError,
)
from app.config.database import get_evidence_payload_settings
from app.domain.identifiers import EvidenceId, InvestigationId, ReportId
from app.presentation.api.auth import AuthenticatedIdentity, require_identity
from app.presentation.api.context import RequestContext, get_request_context
from app.presentation.api.errors import (
    InvalidPayloadError,
    PayloadTooLargeError,
)
from app.presentation.api.generation import (
    Clock,
    IdGenerator,
    get_clock,
    get_id_generator,
)
from app.presentation.api.response import ApiResponse, build_success
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_runner,
    get_investigation_service,
)
from app.presentation.api.v1.investigation.schemas import (
    EvidenceCreateRequest,
    EvidencePayloadStoredResponse,
    EvidenceResponse,
    FindingCreateRequest,
    FindingResponse,
    FindingUpdateRequest,
    InvestigationCreateRequest,
    InvestigationResponse,
    InvestigationStatusChangeRequest,
    OutcomeResponse,
    ReportCreateRequest,
    ReportResponse,
    RunResponse,
    TraceEntryResponse,
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
    identity: AuthenticatedIdentity = Depends(require_identity),
    ids: IdGenerator = Depends(get_id_generator),
    clock: Clock = Depends(get_clock),
) -> ApiResponse[InvestigationResponse]:
    # owner==subject (ES-062) and tenant from the identity's scope (ES-063,
    # ADR-016): both are derived from the authenticated creator, never
    # client-supplied — a client can neither own nor place an investigation
    # in a foreign tenant. The verified identity is established by the
    # router-level authorization chain and reused here (cached).
    investigation = body.to_domain(
        id_value=ids.new_id(),
        owner=identity.subject,
        tenant=identity.tenant,
        created_at=clock.now(),
    )
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


@investigation_router.delete(
    "/investigations/{investigation_id}",
    response_model=ApiResponse[InvestigationResponse],
)
async def erase_investigation(
    investigation_id: str,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
    clock: Clock = Depends(get_clock),
) -> ApiResponse[InvestigationResponse]:
    """Erase an investigation and its investigation-scoped objects (ADR-017).

    Tombstones the investigation (status ``erased``, personal content redacted,
    ``erased_at`` stamped) and cascades to its evidence, outcome and trace;
    findings/reports remain as structural reference tombstones. Owner+tenant
    scoped like every investigation-scoped surface (the ``investigation_id`` path
    param routes through the §6a policy). Idempotent: re-erasing returns the
    same tombstone. Physical erasure of referenced payload bytes is ES-065.
    """

    investigation = await service.erase(
        InvestigationId(investigation_id), clock.now()
    )
    return build_success(InvestigationResponse.from_domain(investigation), context)


# ------------------------------------------------------------------------- run


@investigation_router.post(
    "/investigations/{investigation_id}/run",
    response_model=ApiResponse[RunResponse],
)
async def run_investigation(
    investigation_id: str,
    runner: InvestigationRunner = Depends(get_investigation_runner),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[RunResponse]:
    """Run the Investigation Loop synchronously within the cycle budget.

    The AI Runtime decides and executes one action per cycle; every decision,
    execution and outcome is recorded into the Investigation Trace. A provider
    failure never fails the request: the run returns an ``escalated`` outcome
    with its stable ``failure_code`` (ADR-013) and the investigation remains
    intact.
    """

    outcome = await runner.run(InvestigationId(investigation_id))
    return build_success(RunResponse.from_outcome(outcome), context)


# ----------------------------------------------------------------------- trace


@investigation_router.get(
    "/investigations/{investigation_id}/trace",
    response_model=ApiResponse[list[TraceEntryResponse]],
)
async def list_trace(
    investigation_id: str,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[list[TraceEntryResponse]]:
    """Return the investigation's explainability trace in append order.

    An investigation without trace entries yields an empty list, not an
    error. The trace is read-only over HTTP: entries are produced by the
    platform (the Investigation Loop and, later, other recorded steps).
    """

    entries = await service.list_trace(InvestigationId(investigation_id))
    return build_success(
        [TraceEntryResponse.from_domain(entry) for entry in entries], context
    )


# --------------------------------------------------------------------- outcome


@investigation_router.get(
    "/investigations/{investigation_id}/outcome",
    response_model=ApiResponse[OutcomeResponse],
)
async def get_outcome(
    investigation_id: str,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[OutcomeResponse]:
    """Return the investigation's synthesized outcome (0..1).

    Read-only over HTTP: outcome creation stays a service-internal operation
    until the Decision Engine arrives. A missing outcome is a stable error
    (``investigation.outcome_not_found``), distinct from an unknown
    investigation.
    """

    outcome = await service.get_outcome(InvestigationId(investigation_id))
    return build_success(OutcomeResponse.from_domain(outcome), context)


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


# ----------------------------------------------------------- evidence payload


@investigation_router.post(
    "/investigations/{investigation_id}/evidence/payloads",
    response_model=ApiResponse[EvidencePayloadStoredResponse],
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/octet-stream": {}},
        }
    },
)
async def store_evidence_payload(
    investigation_id: str,
    request: Request,
    service: InvestigationService = Depends(get_investigation_service),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[EvidencePayloadStoredResponse]:
    """Store a raw evidence payload (ES-060, ADR-015).

    The body is the raw payload bytes (api-design §8: payloads travel as byte
    streams, not JSON). Size is bounded at this boundary; the returned content
    address is what an evidence record carries as its integrity value.
    """

    limit = get_evidence_payload_settings().max_bytes
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise PayloadTooLargeError(
            f"Evidence payload exceeds the {limit}-byte bound."
        )
    content = await request.body()
    if len(content) > limit:
        raise PayloadTooLargeError(
            f"Evidence payload exceeds the {limit}-byte bound."
        )
    if not content:
        raise InvalidPayloadError("Evidence payload must not be empty.")
    address = await service.store_evidence_payload(
        InvestigationId(investigation_id), content
    )
    return build_success(
        EvidencePayloadStoredResponse(address=address, size_bytes=len(content)),
        context,
    )


@investigation_router.get(
    "/investigations/{investigation_id}/evidence/{evidence_id}/payload",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def download_evidence_payload(
    investigation_id: str,
    evidence_id: str,
    service: InvestigationService = Depends(get_investigation_service),
) -> Response:
    """Return an evidence item's raw payload, verified against its address.

    A byte-stream response (api-design §8/§9: the JSON envelope governs
    structured resources). Evidence without a payload address and dangling
    addresses are 404; a verification mismatch is 409 (integrity fault).
    """

    evidence = await service.get_evidence(EvidenceId(evidence_id))
    if evidence.investigation_id != InvestigationId(investigation_id):
        raise EvidenceNotFoundError(f"Evidence '{evidence_id}' not found.")
    content = await service.get_evidence_payload(EvidenceId(evidence_id))
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", evidence_id) or "payload"
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (
                f'attachment; filename="evidence-{safe_name}.bin"'
            )
        },
    )


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
