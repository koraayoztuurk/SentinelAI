"""Operational observability endpoints.

Exposes the backend deployment unit's operational visibility (Platform Observability
§4): a readiness probe distinct from the liveness ``/health`` endpoint, and an
operational metrics endpoint in the Prometheus text exposition format. These are
unversioned, public operational endpoints (like ``/health``) — they carry no business
data and are not part of the authenticated ``/api`` surface.
"""

import asyncio

from fastapi import APIRouter, Request, Response, status
from starlette.responses import PlainTextResponse

from app.observability import metrics

router = APIRouter(tags=["observability"])

PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# Generous enough for a first pool connect including the Windows localhost
# IPv6-then-IPv4 fallback (~2s spent refusing ::1 before 127.0.0.1 succeeds).
_READINESS_PROBE_TIMEOUT_SECONDS = 5.0


@router.get("/health/ready", summary="Readiness check")
async def readiness(request: Request, response: Response) -> dict[str, str]:
    """Report whether the backend can serve business traffic.

    Readiness reflects startup completion (the persistence registry built on
    ``app.state`` during the lifespan) and reachability of the bound
    authoritative store: since the runtime persistence binding (ES-042) the
    business endpoints require PostgreSQL, so readiness probes it with a
    short-timeout round trip. Distinct from liveness (``/health``), which
    stays store-independent.
    """

    registry = getattr(request.app.state, "persistence", None)
    if registry is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "postgres": "not_initialized"}
    try:
        await asyncio.wait_for(
            registry.ping_postgres(), timeout=_READINESS_PROBE_TIMEOUT_SECONDS
        )
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "postgres": "unavailable"}
    return {"status": "ready", "postgres": "ok"}


@router.get("/metrics", summary="Operational metrics")
def operational_metrics() -> PlainTextResponse:
    """Return operational metrics in the Prometheus text exposition format."""

    return PlainTextResponse(
        metrics.render(), media_type=PROMETHEUS_CONTENT_TYPE
    )
