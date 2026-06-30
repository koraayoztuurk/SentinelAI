"""Authorization decision contract.

Authorization is enforced by the Application Domain (authentication-authorization.md
§6/§7): backend logic — not the presentation or AI layers — decides whether an
authenticated identity may perform an operation. This module defines the
provider-neutral decision contract; the concrete policy (roles, permissions,
resource/investigation ownership, context) is deferred.

``AuthorizationRequest`` carries only the primitives needed to make a decision so
the application layer never depends on the presentation-layer identity model. The
default :class:`DenyAllAuthorizer` denies every operation (least privilege; no
privileges are granted by default) until a concrete policy is configured.
"""

from dataclasses import dataclass
from typing import Protocol

from app.application.authorization.errors import AuthorizationError


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """The operational context evaluated for a single authorization decision."""

    subject: str
    identity_kind: str
    operation: str


class Authorizer(Protocol):
    """Replaceable port that evaluates an authorization decision.

    Returns normally when the operation is permitted and raises
    :class:`AuthorizationError` when it is denied. The concrete policy is deferred.
    """

    async def authorize(self, request: AuthorizationRequest) -> None: ...


class DenyAllAuthorizer:
    """Default authorizer that denies every operation (secure by default).

    No concrete authorization policy is configured yet, so — following least
    privilege — every authenticated operation is denied until one is injected.
    """

    async def authorize(self, request: AuthorizationRequest) -> None:
        raise AuthorizationError("Operation not permitted.")
