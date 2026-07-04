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
class OperationContext:
    """The operation context (authentication-authorization §6b).

    Records on whose behalf an operation runs: the verified identity
    (subject + kind) and the request correlation identifier. Established at
    the API boundary, passed explicitly to the components that need it,
    immutable for the operation's lifetime and never persisted as such —
    persisted records copy the fields they need. Introduced with its first
    consumer, the concrete authorization policy (ES-046).
    """

    subject: str
    identity_kind: str
    correlation_id: str


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """The operational context evaluated for a single authorization decision.

    Extended additively by ES-046: ``correlation_id`` is carried from the
    operation context (§6b) and ``investigation_id`` names the
    investigation-scoped resource of the operation when the boundary can
    identify one (§6a) — ``None`` for non-investigation-scoped operations.
    """

    subject: str
    identity_kind: str
    operation: str
    correlation_id: str = ""
    investigation_id: str | None = None

    @classmethod
    def for_context(
        cls,
        context: OperationContext,
        *,
        operation: str,
        investigation_id: str | None = None,
    ) -> "AuthorizationRequest":
        """Build the decision request from the boundary's operation context."""

        return cls(
            subject=context.subject,
            identity_kind=context.identity_kind,
            operation=operation,
            correlation_id=context.correlation_id,
            investigation_id=investigation_id,
        )


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
