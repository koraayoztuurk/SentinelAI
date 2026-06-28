"""Domain exception hierarchy.

Defines the SentinelAI domain-layer exceptions. Every domain exception derives
from :class:`DomainError`, which in turn derives from the shared-kernel
:class:`~app.shared.exceptions.SentinelAIError`. This lets the presentation layer
translate domain failures into consistent API error responses using the stable
``code`` carried by every exception, without depending on the domain internals.

Only exceptions tied to an invariant that the domain model actually enforces are
defined here. Lifecycle-transition, persistence and workflow errors belong to the
specifications that own those capabilities.
"""

from app.shared.exceptions import SentinelAIError


class DomainError(SentinelAIError):
    """Base class for all domain-layer errors."""

    code = "domain.error"


class BlankValueError(DomainError):
    """Raised when a required string-like value is empty or contains only whitespace."""

    code = "domain.blank_value"


class InvalidConfidenceError(DomainError):
    """Raised when a confidence value is outside the inclusive range [0.0, 1.0]."""

    code = "domain.invalid_confidence"


class MissingSupportingEvidenceError(DomainError):
    """Raised when an object requiring supporting evidence is created without any.

    Enforces Domain Rule 2 (Findings Require Evidence) and Domain Rule 4
    (Relationships Require Supporting Evidence).
    """

    code = "domain.missing_supporting_evidence"
