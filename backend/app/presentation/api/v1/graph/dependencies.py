"""Graph API dependencies.

Provides the Graph Service to the controllers. The concrete Neo4j adapter is
deferred (ES-006 technical debt), so the service has no runtime binding yet: the
default dependency reports this explicitly via ``ServiceNotConfiguredError``
(translated to HTTP 503). Tests override this dependency with an in-memory-backed
service.
"""

from app.application.graph import GraphService
from app.presentation.api.errors import ServiceNotConfiguredError


def get_graph_service() -> GraphService:
    """Return the Graph Service (FastAPI dependency)."""

    raise ServiceNotConfiguredError(
        "The Graph Service has no runtime persistence binding."
    )
