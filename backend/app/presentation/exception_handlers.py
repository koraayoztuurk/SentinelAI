"""Application exception handlers.

Translates application exceptions into the standard API error envelope at the HTTP
boundary (api-design §11). Error responses expose a stable ``code``, a safe
``message`` and the per-request identifiers, and never leak internal implementation
details. Unexpected errors are logged and returned as a generic 500 response.

The full response envelope (request/correlation identifiers, metadata) is provided
by the API foundation (ES-014).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.presentation.api.context import current_context
from app.presentation.api.response import build_error
from app.shared.exceptions import SentinelAIError

logger = logging.getLogger(__name__)


def _error_response(
    request: Request, status_code: int, code: str, message: str
) -> JSONResponse:
    envelope = build_error(code, message, current_context(request))
    return JSONResponse(
        status_code=status_code, content=envelope.model_dump(mode="json")
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the application's exception handlers on the FastAPI app."""

    @app.exception_handler(SentinelAIError)
    async def handle_sentinelai_error(
        request: Request, exc: SentinelAIError
    ) -> JSONResponse:
        logger.warning("Application error: %s", exc.code)
        return _error_response(request, 400, exc.code, exc.message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error processing request")
        return _error_response(
            request,
            500,
            "internal_server_error",
            "An unexpected error occurred.",
        )
