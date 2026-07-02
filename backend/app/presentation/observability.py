"""Operational observability endpoints.

Exposes the backend deployment unit's operational visibility (Platform Observability
§4): a readiness probe distinct from the liveness ``/health`` endpoint, and an
operational metrics endpoint in the Prometheus text exposition format. These are
unversioned, public operational endpoints (like ``/health``) — they carry no business
data and are not part of the authenticated ``/api`` surface.
"""

from fastapi import APIRouter, Request, Response, status
from starlette.responses import PlainTextResponse

from app.observability import metrics

router = APIRouter(tags=["observability"])

PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


@router.get("/health/ready", summary="Readiness check")
def readiness(request: Request, response: Response) -> dict[str, str]:
    """Report whether the backend has completed startup and can accept traffic.

    Readiness reflects startup completion — the persistence registry has been built
    on ``app.state`` during the lifespan. It deliberately does not probe the
    databases: the backend runs without them (the persistence resources are created
    lazily), so readiness means "initialized", distinct from liveness.
    """

    ready = getattr(request.app.state, "persistence", None) is not None
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready"}
    return {"status": "ready"}


@router.get("/metrics", summary="Operational metrics")
def operational_metrics() -> PlainTextResponse:
    """Return operational metrics in the Prometheus text exposition format."""

    return PlainTextResponse(
        metrics.render(), media_type=PROMETHEUS_CONTENT_TYPE
    )
