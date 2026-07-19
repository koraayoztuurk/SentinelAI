"""Authentication: establishing a verified identity at the API boundary.

Implements the Authentication step of the request lifecycle (api-design §6,
authentication-authorization.md): a trusted identity is established before any
protected operation runs ("Identity Before Access"; anonymous access is not
permitted). Authentication only verifies identity — it never evaluates permissions
(authorization is the Application Domain's responsibility, ES-020).

The architecture is technology-independent, so this module defines a replaceable
``Authenticator`` port and the identity model; the concrete identity provider
(JWT / OAuth / session) is deferred. The default ``UnconfiguredAuthenticator``
denies every request, keeping the platform secure by default until a provider is
injected. ``require_identity`` is the enforcement seam applied to the protected
``/api/v1`` router.
"""

import hmac
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from fastapi import Depends, Request

from app.application.authorization import DEFAULT_TENANT
from app.application.secrets import (
    SecretName,
    SecretNotFoundError,
    SecretProvider,
)
from app.presentation.api.context import current_context
from app.presentation.api.errors import AuthenticationError

logger = logging.getLogger(__name__)

DEV_AUTH_TOKEN = SecretName("DEV_AUTH_TOKEN")


class IdentityKind(Enum):
    """The category of an authenticated identity (authentication-authorization §4)."""

    HUMAN = "human"
    SYSTEM = "system"
    EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    """A verified identity associated with a request.

    ``subject`` is the unique, traceable identifier of the actor; ``kind``
    distinguishes human, system and external identities; ``tenant`` is the
    identity's organization scope (ADR-016), defaulting to the single default
    tenant when the credential carries none.
    """

    subject: str
    kind: IdentityKind
    tenant: str = DEFAULT_TENANT

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise AuthenticationError("Authenticated identity must have a subject.")
        if not self.tenant.strip():
            raise AuthenticationError("Authenticated identity must have a tenant.")


class Authenticator(Protocol):
    """Replaceable port that verifies a request's identity.

    Implementations extract whatever credential they require from the request
    (header, cookie, token) and verify it, returning an
    :class:`AuthenticatedIdentity` or raising :class:`AuthenticationError`. The
    port prescribes no specific authentication protocol.
    """

    async def authenticate(self, request: Request) -> AuthenticatedIdentity: ...


class UnconfiguredAuthenticator:
    """Default authenticator that denies every request (secure by default).

    The concrete identity provider is deferred; until one is injected, protected
    endpoints reject all requests.
    """

    async def authenticate(self, request: Request) -> AuthenticatedIdentity:
        raise AuthenticationError("No authentication provider is configured.")


class SharedTokenAuthenticator:
    """Development-grade shared-token bearer authenticator (ES-046, V-3).

    Credential shape: ``Authorization: Bearer <subject>:<token>``, where
    ``<token>`` must match the shared ``DEV_AUTH_TOKEN`` secret resolved
    through the ``SecretProvider`` port (never configuration, never logged).
    The subject is caller-declared — development-grade by design: possession
    of the shared secret gates entry, per-subject credentials belong to the
    production identity provider (second phase). Secure by default: a missing
    secret, a missing/malformed header or a wrong token all yield 401; error
    messages never carry credential material.
    """

    def __init__(self, secrets: SecretProvider) -> None:
        self._secrets = secrets

    async def authenticate(self, request: Request) -> AuthenticatedIdentity:
        header = request.headers.get("Authorization", "")
        scheme, _, credential = header.partition(" ")
        if scheme.lower() != "bearer" or not credential.strip():
            raise AuthenticationError("Missing or malformed bearer credential.")
        subject, separator, token = credential.strip().partition(":")
        if not separator or not subject.strip() or not token:
            raise AuthenticationError("Malformed bearer credential.")
        try:
            expected = self._secrets.resolve(DEV_AUTH_TOKEN).reveal().strip()
        except SecretNotFoundError as exc:
            raise AuthenticationError(
                "No authentication provider is configured."
            ) from exc
        if not hmac.compare_digest(token.encode(), expected.encode()):
            raise AuthenticationError("Invalid credential.")
        return AuthenticatedIdentity(
            subject=subject.strip(), kind=IdentityKind.HUMAN
        )


def get_authenticator() -> Authenticator:
    """Return the active authenticator (FastAPI dependency)."""

    return UnconfiguredAuthenticator()


async def require_identity(
    request: Request,
    authenticator: Authenticator = Depends(get_authenticator),
) -> AuthenticatedIdentity:
    """Establish and record the request's verified identity (enforcement seam)."""

    identity = await authenticator.authenticate(request)
    request.state.identity = identity
    logger.info(
        "authenticated subject=%s kind=%s request_id=%s",
        identity.subject,
        identity.kind.value,
        current_context(request).request_id,
    )
    return identity


def current_identity(request: Request) -> AuthenticatedIdentity:
    """Return the request's authenticated identity, or raise if none was established.

    The typed parallel of :func:`~app.presentation.api.context.current_context` for
    code that holds a request but not the injected dependency. An identity is never
    fabricated: a missing identity raises :class:`AuthenticationError`.
    """

    identity = getattr(request.state, "identity", None)
    if isinstance(identity, AuthenticatedIdentity):
        return identity
    raise AuthenticationError("Request has no authenticated identity.")
