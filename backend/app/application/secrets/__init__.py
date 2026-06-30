"""Secrets package.

Exposes the Application Domain's secret-resolution contract: the typed
``SecretName`` reference, the ``SecretProvider`` port and the ``SecretNotFoundError``
raised when a required secret is unavailable. The protected value primitive
``Secret`` lives in the shared kernel.
"""

from app.application.secrets.errors import SecretNotFoundError
from app.application.secrets.provider import SecretName, SecretProvider

__all__ = [
    "SecretName",
    "SecretProvider",
    "SecretNotFoundError",
]
