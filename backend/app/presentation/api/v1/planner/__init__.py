"""Planner API: the ``/api/v1/planner`` workflow-execution resource.

Exposes the thin controller that delegates single Planner Action execution to the
Planner Service and returns its provenance-bearing execution result.
"""

from app.presentation.api.v1.planner.router import planner_router

__all__ = ["planner_router"]
