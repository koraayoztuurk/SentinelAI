"""Application exception handlers.

Translates application exceptions into consistent JSON error responses at the
HTTP boundary. Following the API Design architecture, error responses expose a
stable ``code`` and a safe ``message`` and never leak internal implementation
details. Unexpected errors are logged and returned as a generic 500 response.

This is the minimal error-translation foundation required by the backend
skeleton. The full response envelope (request/correlation identifiers, metadata)
is introduced by ES-016 (API Foundation).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.shared.exceptions import SentinelAIError

logger = logging.getLogger(__name__)


def _error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    """Register the application's exception handlers on the FastAPI app."""

    @app.exception_handler(SentinelAIError)
    async def handle_sentinelai_error(
        request: Request, exc: SentinelAIError
    ) -> JSONResponse:
        logger.warning("Application error: %s", exc.code)
        return JSONResponse(
            status_code=400, content=_error_body(exc.code, exc.message)
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error processing request")
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "internal_server_error", "An unexpected error occurred."
            ),
        )
