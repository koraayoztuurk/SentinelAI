"""Authorization enforcement at the API boundary.

Implements the Authorization step of the request lifecycle (api-design §6,
authentication-authorization.md §6/§7). The decision authority is the Application
Domain: this seam only *triggers* the decision — it chains authentication to obtain
the verified identity, builds the operation context and delegates to the
application-layer :class:`~app.application.authorization.Authorizer`. The
presentation never decides whether an operation is permitted.

The concrete authorization policy is deferred, so the default authorizer denies
every operation (least privilege). The established authorization context is stored
on ``request.state`` so downstream code (audit, future middleware) can read it
through :func:`current_authorization` without rebuilding it.
"""

import logging

from fastapi import Depends, Request

from app.application.authorization import (
    AuthorizationError,
    AuthorizationRequest,
    Authorizer,
    DenyAllAuthorizer,
    OperationContext,
)
from app.presentation.api.auth import AuthenticatedIdentity, require_identity
from app.presentation.api.context import current_context

logger = logging.getLogger(__name__)


def get_authorizer() -> Authorizer:
    """Return the active authorizer (FastAPI dependency)."""

    return DenyAllAuthorizer()


def build_operation(request: Request) -> str:
    """Build the operation identifier authorized for a request (single source)."""

    return f"{request.method} {request.url.path}"


async def require_authorization(
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    authorizer: Authorizer = Depends(get_authorizer),
) -> None:
    """Evaluate and record the authorization decision (enforcement seam).

    The boundary establishes the §6b operation context (verified identity +
    request correlation) and carries it explicitly into the decision; when
    the matched route names an investigation, the resource reference travels
    with the request so the owner-scoping policy (§6a) can evaluate it.
    """

    context = OperationContext(
        subject=identity.subject,
        identity_kind=identity.kind.value,
        correlation_id=current_context(request).correlation_id,
        tenant=identity.tenant,
    )
    request.state.operation_context = context
    investigation_id = request.path_params.get("investigation_id")
    authorization = AuthorizationRequest.for_context(
        context,
        operation=build_operation(request),
        investigation_id=(
            investigation_id if isinstance(investigation_id, str) else None
        ),
    )
    request.state.authorization = authorization
    await authorizer.authorize(authorization)
    logger.info(
        "authorized subject=%s operation=%s request_id=%s",
        authorization.subject,
        authorization.operation,
        current_context(request).request_id,
    )


def current_authorization(request: Request) -> AuthorizationRequest:
    """Return the request's authorization context, or raise if none was established.

    The typed parallel of :func:`~app.presentation.api.context.current_context` and
    :func:`~app.presentation.api.auth.current_identity`. The context is never
    fabricated: a missing context raises :class:`AuthorizationError`.
    """

    authorization = getattr(request.state, "authorization", None)
    if isinstance(authorization, AuthorizationRequest):
        return authorization
    raise AuthorizationError("Request has no authorization context.")
