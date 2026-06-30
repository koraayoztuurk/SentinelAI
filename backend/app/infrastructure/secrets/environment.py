"""Environment-variable secret provider.

The default :class:`~app.application.secrets.SecretProvider` adapter: it resolves a
secret from the process environment by the secret's name. This keeps the secrets
foundation usable out of the box (consistent with the environment-based
configuration the platform already uses) while the concrete vault adapter is
deferred. A missing or empty variable yields ``SecretNotFoundError``; the value is
never logged.
"""

import os

from app.application.secrets import SecretName, SecretNotFoundError
from app.shared.secret import Secret


class EnvironmentSecretProvider:
    """Resolves secrets from environment variables."""

    def resolve(self, name: SecretName) -> Secret:
        value = os.environ.get(name.value)
        if not value:
            raise SecretNotFoundError(f"Secret '{name.value}' is not available.")
        return Secret(value)
