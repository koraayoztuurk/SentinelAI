"""Secret resolution contract.

The Application Domain is responsible for consuming operational secrets (Secrets
Management §6). This module defines the provider-neutral resolution contract: a
:class:`SecretProvider` resolves a secret by its :class:`SecretName`. The concrete
secret store (a vault, a file, an environment) is an implementation detail provided
by the infrastructure layer; the concrete store and an async variant are deferred.

``SecretName`` is a typed reference rather than a raw string because secret names
are part of the system contract. It is not sensitive (it names a secret, it is not
the value), so it does not require the masking applied to a ``Secret``.
"""

from dataclasses import dataclass
from typing import Protocol

from app.shared.secret import Secret


@dataclass(frozen=True, slots=True)
class SecretName:
    """The typed name of a secret (for example ``SecretName("OPENAI_API_KEY")``)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("SecretName must not be blank.")


class SecretProvider(Protocol):
    """Replaceable port that resolves secrets by name (need-to-know distribution)."""

    def resolve(self, name: SecretName) -> Secret: ...
