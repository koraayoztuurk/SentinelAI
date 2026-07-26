"""Platform status DTOs (ES-070).

The transitional response model of the operational surface: the posture of the
hardening Milestone G delivered, in one read — store readiness (ES-069),
provider resilience and background-projection health (ES-067), the data
lifecycle's configured retention and erasure strategy (ES-070), the audit sink
(ES-069), and the caller's own capabilities (ADR-019).

Deliberately a **read** of platform state, not of business data: it names no
investigation, no analyst and no knowledge. The one caller-specific field is
the capability set, which is the answer to "what may I do here" and therefore
belongs to the caller asking.
"""

from pydantic import BaseModel


class StoreReadinessResponse(BaseModel):
    """Reachability of each bound store, and whether it gates readiness."""

    status: str
    postgres: str
    neo4j: str
    qdrant: str
    gating: list[str]


class ProviderHealthResponse(BaseModel):
    """One AI provider's circuit state (ES-067)."""

    provider: str
    circuit: str


class ResilienceResponse(BaseModel):
    """Provider and background-projection health (ES-067)."""

    providers: list[ProviderHealthResponse]
    llm_fallbacks: int
    projection_dead_letters: dict[str, int]
    payload_erasures_deferred: int


class DataLifecycleResponse(BaseModel):
    """The configured end-of-life posture (ES-070, data-lifecycle §3).

    Durations are deployment policy, so the surface reports what *this*
    deployment chose rather than implying a platform default. A retention of
    zero days means enforcement is off — reported as such rather than as a
    number that looks like a policy.
    """

    retention_days: int
    retention_enforced: bool
    investigations_erased: int
    retention_failures: int
    payload_erasure_strategy: str
    audit_retention_days: int


class AuditPostureResponse(BaseModel):
    """Whether the audit record is durable and tamper-evident (ES-069)."""

    sink: str
    durable: bool
    write_failures: int


class PlatformStatusResponse(BaseModel):
    """The platform's operational posture in one read."""

    environment: str
    version: str
    readiness: StoreReadinessResponse
    resilience: ResilienceResponse
    data_lifecycle: DataLifecycleResponse
    audit: AuditPostureResponse
    capabilities: list[str]
