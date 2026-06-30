"""Version 1 of the SentinelAI business API.

Exposes the ``/api/v1`` router that aggregates the resource routers (Investigation,
Graph, Memory, Planner). The router carries a router-level ``require_authorization``
dependency (ES-020), which chains authentication (ES-019): every business endpoint
requires a verified identity (else 401) and an authorized operation (else 403)
before execution; the operational ``/health`` endpoint stays public.
"""

from fastapi import APIRouter, Depends

from app.presentation.api.authorization import require_authorization
from app.presentation.api.v1.graph import graph_router
from app.presentation.api.v1.investigation import investigation_router
from app.presentation.api.v1.memory import memory_router
from app.presentation.api.v1.planner import planner_router

api_v1_router = APIRouter(
    prefix="/api/v1", dependencies=[Depends(require_authorization)]
)
api_v1_router.include_router(investigation_router)
api_v1_router.include_router(graph_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(planner_router)
