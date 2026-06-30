"""Audit enforcement at the API boundary.

Records a security-relevant audit event for every protected ``/api`` request,
implementing the Backend's audit responsibility (audit-and-observability.md §6)
without modifying the authentication/authorization seams. The middleware reads the
authorization context that ``require_authorization`` already stored on
``request.state`` (ES-020) plus the HTTP outcome, so it never rebuilds the request
context.

Recording is best-effort: a recorder failure is logged and swallowed so audit never
drops a business request (the durable, tamper-resistant store is deferred). Audit is
distinct from the operational request logging (observability).
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.application.audit import AuditAction, AuditEvent, AuditOutcome
from app.application.authorization import AuthorizationRequest
from app.presentation.api.authorization import build_operation
from app.presentation.api.context import current_context

logger = logging.getLogger(__name__)

_AUDITED_PREFIX = "/api/"


class AuditMiddleware(BaseHTTPMiddleware):
    """Records a best-effort audit event for each protected request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith(_AUDITED_PREFIX):
            await self._record(request, response.status_code)
        return response

    @staticmethod
    async def _record(request: Request, status_code: int) -> None:
        event = _build_event(request, status_code)
        recorder = request.app.state.audit_recorder
        try:
            await recorder.record(event)
        except Exception:  # best-effort: audit must never drop a request
            logger.exception("Audit recording failed")


def _build_event(request: Request, status_code: int) -> AuditEvent:
    authorization = getattr(request.state, "authorization", None)
    request_id = current_context(request).request_id

    if status_code == 401:
        return AuditEvent(
            action=AuditAction.AUTHENTICATION_FAILED,
            outcome=AuditOutcome.FAILED,
            subject=None,
            identity_kind=None,
            operation=build_operation(request),
            request_id=request_id,
        )

    subject = (
        authorization.subject
        if isinstance(authorization, AuthorizationRequest)
        else None
    )
    identity_kind = (
        authorization.identity_kind
        if isinstance(authorization, AuthorizationRequest)
        else None
    )
    operation = (
        authorization.operation
        if isinstance(authorization, AuthorizationRequest)
        else build_operation(request)
    )

    if status_code == 403:
        return AuditEvent(
            action=AuditAction.AUTHORIZATION_DENIED,
            outcome=AuditOutcome.DENIED,
            subject=subject,
            identity_kind=identity_kind,
            operation=operation,
            request_id=request_id,
        )

    outcome = (
        AuditOutcome.SUCCEEDED
        if 200 <= status_code < 300
        else AuditOutcome.FAILED
    )
    return AuditEvent(
        action=AuditAction.OPERATION_PERFORMED,
        outcome=outcome,
        subject=subject,
        identity_kind=identity_kind,
        operation=operation,
        request_id=request_id,
    )
