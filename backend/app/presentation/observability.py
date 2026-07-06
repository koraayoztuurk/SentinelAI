"""Operational observability endpoints.

Exposes the backend deployment unit's operational visibility (Platform Observability
§4): a readiness probe distinct from the liveness ``/health`` endpoint, and an
operational metrics endpoint in the Prometheus text exposition format. These are
unversioned, public operational endpoints (like ``/health``) — they carry no business
data and are not part of the authenticated ``/api`` surface.
"""

import asyncio
from collections.abc import Awaitable
from typing import Any

from fastapi import APIRouter, Request, Response, status
from starlette.responses import PlainTextResponse

from app.observability import metrics

router = APIRouter(tags=["observability"])

PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# Generous enough for a first pool connect including the Windows localhost
# IPv6-then-IPv4 fallback (~2s spent refusing ::1 before 127.0.0.1 succeeds).
_READINESS_PROBE_TIMEOUT_SECONDS = 5.0


async def _probe(coro: Awaitable[Any]) -> str:
    """Return "ok" if the probe succeeds within the bound, else "unavailable"."""

    try:
        await asyncio.wait_for(coro, timeout=_READINESS_PROBE_TIMEOUT_SECONDS)
    except Exception:
        return "unavailable"
    return "ok"


@router.get("/health/ready", summary="Readiness check")
async def readiness(request: Request, response: Response) -> dict[str, str]:
    """Report whether the backend can serve business traffic.

    Readiness reflects startup completion (the persistence registry built on
    ``app.state`` during the lifespan) and the reachability of the bound stores.
    **PostgreSQL is the authoritative core**: without it no business flow works,
    so it **gates** overall readiness. Neo4j (the graph store, bound since
    ES-048) is **probed and reported truthfully** but does not gate readiness —
    graph operations degrade to contained failures by design (planner-service
    §8), so a graph-store blip must not take the whole platform out of
    rotation. Distinct from liveness (``/health``), which is store-independent.
    """

    registry = getattr(request.app.state, "persistence", None)
    if registry is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "postgres": "not_initialized",
            "neo4j": "not_initialized",
        }

    postgres = await _probe(registry.ping_postgres())
    neo4j = await _probe(registry.ping_neo4j())
    body = {"status": "ready", "postgres": postgres, "neo4j": neo4j}
    if postgres != "ok":
        body["status"] = "not_ready"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return body


@router.get("/metrics", summary="Operational metrics")
def operational_metrics() -> PlainTextResponse:
    """Return operational metrics in the Prometheus text exposition format."""

    return PlainTextResponse(
        metrics.render(), media_type=PROMETHEUS_CONTENT_TYPE
    )
