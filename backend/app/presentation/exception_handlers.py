"""Application exception handlers.

Translates application, domain and request-validation failures into the standard
API error envelope at the HTTP boundary (api-design §11). Application/domain errors
are mapped to HTTP status codes by their stable ``code`` (``http_status_for``);
structural request-validation failures are reported consistently; unexpected errors
are logged and returned as a generic 500. Error responses carry the per-request
identifiers and never leak internal implementation details.

The full response envelope (request/correlation identifiers, metadata) is provided
by the API foundation (ES-014).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.presentation.api.context import current_context
from app.presentation.api.error_status import http_status_for
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
        return _error_response(
            request, http_status_for(exc), exc.code, exc.message
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("Request validation failed")
        return _error_response(
            request,
            422,
            "api.validation_error",
            "Request validation failed.",
        )

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
