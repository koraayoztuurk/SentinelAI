"""Investigation API dependencies.

Provides the Investigation Service to the controllers. The concrete persistence
adapters are deferred (ES-005 technical debt), so the service has no runtime
binding yet: the default dependency reports this explicitly via
``ServiceNotConfiguredError`` (translated to HTTP 503). Tests override this
dependency with an in-memory-backed service.
"""

from app.ai.orchestration.runner import InvestigationRunner
from app.application.investigation import InvestigationService
from app.presentation.api.errors import ServiceNotConfiguredError


def get_investigation_service() -> InvestigationService:
    """Return the Investigation Service (FastAPI dependency)."""

    raise ServiceNotConfiguredError(
        "The Investigation Service has no runtime persistence binding."
    )


def get_investigation_runner() -> InvestigationRunner:
    """Return the Investigation run composition (FastAPI dependency)."""

    raise ServiceNotConfiguredError(
        "The Investigation Loop has no runtime binding."
    )
