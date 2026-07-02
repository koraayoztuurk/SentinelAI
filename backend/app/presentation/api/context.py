"""Request context: per-request identifiers and propagation.

Establishes the communication-layer request context required by the API Design
architecture (api-design §6/§9): every request receives a request identifier and a
correlation identifier for distributed tracing. These identifiers and timestamps
are a **presentation/transport concern** — the "no UUID/clock in domain/services"
rule constrains the domain and backend services, not the HTTP boundary.

The middleware assigns the identifiers, stores them on ``request.state``, echoes
them on response headers and records lightweight lifecycle logging (no secrets or
payloads). Endpoints obtain the context through the ``get_request_context``
dependency; the exception handlers read it through ``current_context``.
"""

import logging
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.observability import Correlation, bind, metrics, reset

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
PROCESS_TIME_HEADER = "X-Process-Time"


@dataclass(frozen=True, slots=True)
class RequestContext:
    """The per-request identifiers carried through the request lifecycle."""

    request_id: str
    correlation_id: str


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns and propagates the per-request context."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = uuid4().hex
        correlation_id = (
            request.headers.get(CORRELATION_ID_HEADER) or request_id
        )
        context = RequestContext(
            request_id=request_id, correlation_id=correlation_id
        )
        request.state.request_context = context

        # Bind the correlation for the duration of the request so every log record
        # emitted while handling it carries the identifiers (end-to-end traceability).
        token = bind(
            Correlation(request_id=request_id, correlation_id=correlation_id)
        )
        started_at = perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (perf_counter() - started_at) * 1000.0

            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            response.headers[PROCESS_TIME_HEADER] = f"{duration_ms:.3f}"

            metrics.record_request(
                request.method, response.status_code, duration_ms
            )
            logger.info(
                "request method=%s path=%s status=%s correlation_id=%s "
                "duration_ms=%.3f",
                request.method,
                request.url.path,
                response.status_code,
                correlation_id,
                duration_ms,
            )
            return response
        finally:
            reset(token)


def get_request_context(request: Request) -> RequestContext:
    """Return the current request context (FastAPI dependency)."""

    return current_context(request)


def current_context(request: Request) -> RequestContext:
    """Return the request context, synthesizing one if it is missing.

    The middleware always sets the context, but error responses must still carry a
    request identifier even if a failure occurs before the context is established.
    """

    context = getattr(request.state, "request_context", None)
    if isinstance(context, RequestContext):
        return context
    request_id = uuid4().hex
    return RequestContext(request_id=request_id, correlation_id=request_id)
