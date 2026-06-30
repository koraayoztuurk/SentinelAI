"""Secrets exceptions.

Application-layer error for secret resolution. It derives from the shared
:class:`~app.shared.exceptions.SentinelAIError` and carries a stable
machine-readable ``code``. The message never includes a secret value.
"""

from app.shared.exceptions import SentinelAIError


class SecretNotFoundError(SentinelAIError):
    """Raised when a required secret is not available from the provider."""

    code = "secret.not_found"
