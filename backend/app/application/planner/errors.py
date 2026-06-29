"""Planner Service exceptions.

Service-level errors raised by the Planner Service. Each derives from the shared
:class:`~app.shared.exceptions.SentinelAIError` and carries a stable
machine-readable ``code``. Only errors tied to an enforced rule are defined here;
failures from downstream services are surfaced as a failed
:class:`~app.application.planner.actions.ExecutionResult` rather than raised.
"""

from app.shared.exceptions import SentinelAIError


class PlannerServiceError(SentinelAIError):
    """Base class for Planner Service errors."""

    code = "planner.error"


class InvalidActionError(PlannerServiceError):
    """Raised when a Planner Action is malformed (for example a blank action id
    or non-positive traversal limits)."""

    code = "planner.invalid_action"
