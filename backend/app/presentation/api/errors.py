"""API-layer errors.

Presentation-layer failures that are not raised by a backend service. They derive
from :class:`~app.shared.exceptions.SentinelAIError` so the standard error envelope
and status translation apply uniformly.
"""

from app.shared.exceptions import SentinelAIError


class ServiceNotConfiguredError(SentinelAIError):
    """Raised when a backend service has no runtime persistence binding.

    The concrete persistence adapters are deferred (ES-005 technical debt); until
    they exist the service dependency is unbound and reports this explicitly
    (translated to HTTP 503).
    """

    code = "api.persistence_not_configured"


class PersistenceUnavailableError(SentinelAIError):
    """Raised when the bound persistence store cannot be reached at runtime.

    Distinct from :class:`ServiceNotConfiguredError`: the runtime binding
    exists (ES-042) but PostgreSQL is unreachable — an operational condition,
    not a configuration gap. Translated to HTTP 503.
    """

    code = "api.persistence_unavailable"


class AuthenticationError(SentinelAIError):
    """Raised when a request cannot be associated with a verified identity.

    Covers a missing, malformed or rejected credential and an unconfigured
    authentication provider. Translated to HTTP 401; the message never reveals
    unnecessary security details.
    """

    code = "api.unauthenticated"


class PayloadTooLargeError(SentinelAIError):
    """Raised when an uploaded evidence payload exceeds the configured bound.

    The bound (``EVIDENCE_PAYLOAD_MAX_BYTES``) is enforced at the API boundary
    before the payload reaches the owning service. Translated to HTTP 413.
    """

    code = "api.payload_too_large"


class InvalidPayloadError(SentinelAIError):
    """Raised when an uploaded evidence payload body is structurally invalid
    (for example, empty). Translated to HTTP 422."""

    code = "api.invalid_payload"
