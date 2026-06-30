"""Version 1 of the SentinelAI business API.

Exposes the ``/api/v1`` router that aggregates the resource routers (Investigation,
Graph, Memory, Planner). The router carries a router-level ``require_identity``
dependency (ES-019), so every business endpoint requires a verified identity before
execution; the operational ``/health`` endpoint stays public.
"""

from fastapi import APIRouter, Depends

from app.presentation.api.auth import require_identity
from app.presentation.api.v1.graph import graph_router
from app.presentation.api.v1.investigation import investigation_router
from app.presentation.api.v1.memory import memory_router
from app.presentation.api.v1.planner import planner_router

api_v1_router = APIRouter(
    prefix="/api/v1", dependencies=[Depends(require_identity)]
)
api_v1_router.include_router(investigation_router)
api_v1_router.include_router(graph_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(planner_router)
