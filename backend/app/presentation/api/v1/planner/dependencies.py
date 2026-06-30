"""Planner API dependencies.

Provides the Planner Service to the controller. The Planner Service orchestrates
the Investigation, Graph and Memory services, whose concrete persistence adapters
are all deferred (ES-005/006/007 technical debt), so it has no runtime binding yet:
the default dependency reports this explicitly via ``ServiceNotConfiguredError``
(translated to HTTP 503). Tests override this dependency with an in-memory-backed
Planner Service.
"""

from app.application.planner import PlannerService
from app.presentation.api.errors import ServiceNotConfiguredError


def get_planner_service() -> PlannerService:
    """Return the Planner Service (FastAPI dependency)."""

    raise ServiceNotConfiguredError(
        "The Planner Service has no runtime persistence binding."
    )
