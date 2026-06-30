"""Authorization exceptions.

Service-level error raised by the Application Domain's authorization decision. It
derives from the shared :class:`~app.shared.exceptions.SentinelAIError` and carries
a stable machine-readable ``code`` so the API layer can translate it consistently.
The message stays minimal and never reveals unnecessary security details
(authentication-authorization.md §8).
"""

from app.shared.exceptions import SentinelAIError


class AuthorizationError(SentinelAIError):
    """Raised when an authenticated identity may not perform the requested operation."""

    code = "authorization.denied"
