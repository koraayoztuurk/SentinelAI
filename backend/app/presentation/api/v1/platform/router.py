"""Platform status endpoint (ES-070).

The user-visible leg of the production-hardening milestone. Everything
ES-067/068/069 added works silently by design — a breaker that never opens, a
projection that never dead-letters, an audit chain nobody reads — so the
milestone's honest deliverable is a surface that makes the posture legible to
the people responsible for it.

It is **authenticated but not privileged**: it exposes the platform's own
condition, never business data, so any identity that may use the API may see
whether the platform it is using is healthy. It is deliberately separate from
``/health/ready`` and ``/metrics``, which answer an orchestrator and a scraper
on the internal network and are not part of the business API (the production
edge refuses them from outside).
"""

from fastapi import APIRouter, Depends, Request

from app import __version__
from app.config.audit import AuditSinkChoice, get_audit_settings
from app.config.database import get_evidence_payload_settings
from app.config.settings import get_settings
from app.observability import metrics
from app.presentation.api.auth import AuthenticatedIdentity, require_identity
from app.presentation.api.context import RequestContext, get_request_context
from app.presentation.api.response import ApiResponse, build_success
from app.presentation.api.v1.platform.schemas import (
    AuditPostureResponse,
    DataLifecycleResponse,
    PlatformStatusResponse,
    ProviderHealthResponse,
    ResilienceResponse,
    StoreReadinessResponse,
)
from app.presentation.observability import probe_stores

platform_router = APIRouter(prefix="/platform", tags=["platform"])


@platform_router.get(
    "/status",
    response_model=ApiResponse[PlatformStatusResponse],
)
async def platform_status(
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    context: RequestContext = Depends(get_request_context),
) -> ApiResponse[PlatformStatusResponse]:
    """Report the platform's operational posture.

    Store readiness is probed live; resilience and lifecycle counters come from
    the in-process observability registry, so the numbers describe **this
    instance** — the same scope the metrics endpoint reports, and the honest
    one until the platform runs as a cluster.
    """

    settings = get_settings()
    audit = get_audit_settings()
    payloads = get_evidence_payload_settings()
    readiness = await probe_stores(request)
    signals = metrics.snapshot()

    return build_success(
        PlatformStatusResponse(
            environment=settings.app_env,
            version=__version__,
            readiness=StoreReadinessResponse.model_validate(readiness),
            resilience=ResilienceResponse(
                providers=[
                    ProviderHealthResponse(provider=provider, circuit=state)
                    for provider, state in sorted(signals.breaker_states.items())
                ],
                llm_fallbacks=signals.llm_fallbacks,
                projection_dead_letters=signals.dead_letters,
                payload_erasures_deferred=signals.deferred_erasures,
            ),
            data_lifecycle=DataLifecycleResponse(
                retention_days=settings.retention_investigation_days,
                retention_enforced=settings.retention_investigation_days > 0,
                investigations_erased=signals.retention_erased,
                retention_failures=signals.retention_failed,
                payload_erasure_strategy=(
                    "crypto_shred" if payloads.crypto_shred else "delete"
                ),
                audit_retention_days=audit.retention_days,
            ),
            audit=AuditPostureResponse(
                sink=audit.sink.value,
                durable=audit.sink is AuditSinkChoice.DURABLE,
                write_failures=signals.audit_failures,
            ),
            capabilities=sorted(identity.capabilities),
        ),
        context,
    )
