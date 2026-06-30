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


class AuthenticationError(SentinelAIError):
    """Raised when a request cannot be associated with a verified identity.

    Covers a missing, malformed or rejected credential and an unconfigured
    authentication provider. Translated to HTTP 401; the message never reveals
    unnecessary security details.
    """

    code = "api.unauthenticated"
