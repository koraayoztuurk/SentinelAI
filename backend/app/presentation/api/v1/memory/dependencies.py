"""Memory API dependencies.

Provides the Memory Service to the controllers. The concrete PostgreSQL adapter is
deferred (ES-007 technical debt), so the service has no runtime binding yet: the
default dependency reports this explicitly via ``ServiceNotConfiguredError``
(translated to HTTP 503). Tests override this dependency with an in-memory-backed
service.
"""

from app.application.memory import MemoryService
from app.presentation.api.errors import ServiceNotConfiguredError


def get_memory_service() -> MemoryService:
    """Return the Memory Service (FastAPI dependency)."""

    raise ServiceNotConfiguredError(
        "The Memory Service has no runtime persistence binding."
    )
