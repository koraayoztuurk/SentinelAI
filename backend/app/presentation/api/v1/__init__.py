"""Version 1 of the SentinelAI business API.

Exposes the ``/api/v1`` router that aggregates the resource routers. The router is
intentionally empty in the API foundation; the resource-specific routers
(Investigation, Graph, Memory, Workflow) are attached by the specifications that
follow (ES-015+).
"""

from fastapi import APIRouter

from app.presentation.api.v1.graph import graph_router
from app.presentation.api.v1.investigation import investigation_router
from app.presentation.api.v1.memory import memory_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(investigation_router)
api_v1_router.include_router(graph_router)
api_v1_router.include_router(memory_router)
