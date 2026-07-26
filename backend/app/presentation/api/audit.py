"""Audit enforcement at the API boundary.

Records a security-relevant audit event for every protected ``/api`` request,
implementing the Backend's audit responsibility (audit-and-observability.md §6)
without modifying the authentication/authorization seams. The middleware reads the
authorization context that ``require_authorization`` already stored on
``request.state`` (ES-020) plus the HTTP outcome, so it never rebuilds the request
context.

Recording is contained: a sink failure is logged, counted and the event is still
emitted to the log sink, so audit never drops a business request and never loses
an event silently (ADR-018 §8). Audit is distinct from the operational request
logging (observability).
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.application.audit import (
    AuditAction,
    AuditEvent,
    AuditOutcome,
    LoggingAuditRecorder,
)
from app.application.authorization import AuthorizationRequest
from app.observability import metrics
from app.presentation.api.auth import AuthenticatedIdentity
from app.presentation.api.authorization import build_operation
from app.presentation.api.context import current_context, route_template

logger = logging.getLogger(__name__)

_AUDITED_PREFIX = "/api/"

# The one operation that ends an investigation's life (ADR-017).
ERASE_OPERATION = "/api/v1/investigations/{investigation_id}"

# The degraded path when the durable sink is unreachable (ADR-018 §8): the
# event is worth less in a log than in the chain, but it is worth far more
# there than nowhere.
_FALLBACK_RECORDER = LoggingAuditRecorder()


class AuditMiddleware(BaseHTTPMiddleware):
    """Records an audit event for each protected request."""

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
        except Exception:
            # Audit must never take down the operation it observes (ES-021),
            # but an unrecorded action is an accountability gap — so it is
            # loud, and the event still reaches the log sink.
            logger.exception("Audit recording failed")
            metrics.record_audit_failure()
            try:
                await _FALLBACK_RECORDER.record(event)
            except Exception:  # pragma: no cover - the log sink is in-process
                logger.exception("Audit fallback recording failed")


def _affected_resource(request: Request) -> str | None:
    """Return the identifier of the resource the request addressed.

    The **last** path parameter, which is the most specific one the route
    named: for ``/investigations/{id}/evidence/{evidence_id}`` the affected
    resource is the evidence item, not its investigation. An identifier only —
    an audit record never carries content (ADR-018 §6).
    """

    values = [
        value
        for value in request.path_params.values()
        if isinstance(value, str) and value
    ]
    return values[-1] if values else None


def _action_for(request: Request, status_code: int) -> AuditAction:
    """Map the request outcome onto the audit vocabulary (ADR-018 §7)."""

    if status_code == 401:
        return AuditAction.AUTHENTICATION_FAILED
    if status_code == 403:
        return AuditAction.AUTHORIZATION_DENIED
    if status_code == 429:
        return AuditAction.TRAFFIC_LIMIT_ENFORCED
    if (
        request.method == "DELETE"
        and 200 <= status_code < 300
        # Matched against the *exact* operation rather than "a DELETE with an
        # investigation id in the path": a future DELETE of a sub-resource
        # would otherwise be recorded as an investigation erasure, and a
        # mis-stated action in a retention-bound compliance record is the last
        # place to accept an approximation.
        and route_template(request) == ERASE_OPERATION
    ):
        # data-lifecycle.md §5 requires the record of *who erased what* to
        # outlive the erased data, so an erasure is recorded as an erasure
        # rather than as an anonymous operation (the ES-064 deferral).
        return AuditAction.INVESTIGATION_ERASED
    return AuditAction.OPERATION_PERFORMED


def _build_event(request: Request, status_code: int) -> AuditEvent:
    authorization = getattr(request.state, "authorization", None)
    identity = getattr(request.state, "identity", None)
    request_id = current_context(request).request_id
    action = _action_for(request, status_code)
    resource = _affected_resource(request)

    if action is AuditAction.AUTHENTICATION_FAILED:
        return AuditEvent(
            action=action,
            outcome=AuditOutcome.FAILED,
            subject=None,
            identity_kind=None,
            operation=build_operation(request),
            request_id=request_id,
            resource=resource,
        )

    if isinstance(authorization, AuthorizationRequest):
        subject = authorization.subject
        identity_kind = authorization.identity_kind
        operation = authorization.operation
    elif isinstance(identity, AuthenticatedIdentity):
        # Authenticated but refused before the authorization decision — a
        # rate-limited request (429, ES-068). The identity is known, so
        # recording the event as anonymous would drop exactly the actor the
        # event is about.
        subject = identity.subject
        identity_kind = identity.kind.value
        operation = build_operation(request)
    else:
        subject = None
        identity_kind = None
        operation = build_operation(request)

    if action in (
        AuditAction.AUTHORIZATION_DENIED,
        # A refused request is a denial, not a failure: nothing went wrong,
        # the platform declined (ES-068).
        AuditAction.TRAFFIC_LIMIT_ENFORCED,
    ):
        outcome = AuditOutcome.DENIED
    elif 200 <= status_code < 300:
        outcome = AuditOutcome.SUCCEEDED
    else:
        outcome = AuditOutcome.FAILED

    return AuditEvent(
        action=action,
        outcome=outcome,
        subject=subject,
        identity_kind=identity_kind,
        operation=operation,
        request_id=request_id,
        resource=resource,
    )
