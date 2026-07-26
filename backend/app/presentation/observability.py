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


# Which stores gate readiness (platform-observability §4, ES-069). The rule is
# ownership, not preference: a store holding data the platform is
# **authoritative** for is gating, because the unit cannot fulfil its business
# responsibility without it. PostgreSQL owns the Investigation family, Memory
# and audit (ADR-003/ADR-018); Neo4j owns the Knowledge Graph since ES-048 —
# graph writes have nowhere else to go, so an unreachable graph store is a
# capability the unit cannot provide, not a degradation it can absorb.
#
# Qdrant is **derived** (ADR-011/ADR-012): its embeddings are reproducible from
# PostgreSQL, and semantic retrieval already degrades to a contained failure. It
# is probed and reported truthfully but never gates — gating on a derived store
# would convert a partial capability loss into a total outage.
_GATING_STORES = ("postgres", "neo4j")
_DEGRADABLE_STORES = ("qdrant",)


async def probe_stores(request: Request) -> dict[str, object]:
    """Probe every bound store and report readiness (ES-069/ES-070).

    Shared by the readiness probe and the platform status surface so the two
    can never disagree about whether the platform is ready — one of them
    telling an operator something different from the other is worse than
    either being wrong alone.
    """

    registry = getattr(request.app.state, "persistence", None)
    if registry is None:
        return {
            "status": "not_ready",
            "postgres": "not_initialized",
            "neo4j": "not_initialized",
            "qdrant": "not_initialized",
            "gating": list(_GATING_STORES),
        }

    body: dict[str, object] = {
        "status": "ready",
        "postgres": await _probe(registry.ping_postgres()),
        "neo4j": await _probe(registry.ping_neo4j()),
        "qdrant": await _probe(registry.ping_qdrant()),
        "gating": list(_GATING_STORES),
    }
    if any(body[store] != "ok" for store in _GATING_STORES):
        body["status"] = "not_ready"
    elif any(body[store] != "ok" for store in _DEGRADABLE_STORES):
        # Reported, never gating: an operator must be able to see a degraded
        # dependency without the platform having to fail to disclose it.
        body["status"] = "degraded"
    return body


@router.get("/health/ready", summary="Readiness check")
async def readiness(request: Request, response: Response) -> dict[str, str]:
    """Report whether the backend can serve business traffic.

    Readiness reflects startup completion and the reachability of the bound
    stores. Every store is probed and reported truthfully. A store holding data
    the platform is authoritative for **gates** the verdict: unreachable means
    ``not_ready``. A store holding a derived representation does not gate;
    unreachable means ``degraded`` — reported, still serving. Distinct from
    liveness (``/health``), which is store-independent: an unreachable store is
    not a reason to restart a healthy process.
    """

    probed = await probe_stores(request)
    if probed["status"] == "not_ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    # The probe surface carries the gating list for the platform status
    # endpoint; the orchestrator's probe answers with store states only.
    return {
        key: value
        for key, value in probed.items()
        if key != "gating" and isinstance(value, str)
    }


@router.get("/metrics", summary="Operational metrics")
def operational_metrics() -> PlainTextResponse:
    """Return operational metrics in the Prometheus text exposition format."""

    return PlainTextResponse(
        metrics.render(), media_type=PROMETHEUS_CONTENT_TYPE
    )
