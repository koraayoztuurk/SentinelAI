"""Test support for the authenticated identity seam (ES-062).

Presentation tests that bypass the router authorization chain
(``require_authorization`` overridden to a no-op) still need the create
endpoint's verified identity, since ``owner`` is now derived from the
authenticated subject rather than the request body. This helper installs a
fixed identity so those tests keep exercising the endpoints without a real
credential — the real auth chain is validated separately (owner-scoped and
auth-chain suites).
"""

from fastapi import FastAPI

from app.presentation.api.auth import (
    AuthenticatedIdentity,
    IdentityKind,
    require_identity,
)


def override_identity(
    app: FastAPI,
    subject: str = "analyst-1",
    kind: IdentityKind = IdentityKind.HUMAN,
) -> None:
    """Override the endpoint identity dependency with a fixed identity."""

    identity = AuthenticatedIdentity(subject=subject, kind=kind)
    app.dependency_overrides[require_identity] = lambda: identity
