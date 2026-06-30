"""Version 1 of the SentinelAI business API.

Exposes the ``/api/v1`` router that aggregates the resource routers. The router is
intentionally empty in the API foundation; the resource-specific routers
(Investigation, Graph, Memory, Workflow) are attached by the specifications that
follow (ES-015+).
"""

from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")
