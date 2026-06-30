"""Standard API response envelopes.

Defines the consistent success and error response structures required by the API
Design architecture (api-design §9/§11). Every response carries a stable status, a
metadata block (request/correlation identifiers, timestamp, API version) and either
a typed ``data`` payload or a structured ``error``.

Endpoints (introduced by ES-015+) wrap their service results with
``build_success`` (the explicit-helper style); the exception handlers build error
envelopes with ``build_error``. Timestamps are generated here as a transport
concern.
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel

from app.presentation.api import API_VERSION
from app.presentation.api.context import RequestContext


class ResponseStatus(Enum):
    """The outcome status carried by every API response."""

    SUCCESS = "success"
    ERROR = "error"


class ResponseMeta(BaseModel):
    """Response metadata common to success and error responses."""

    request_id: str
    correlation_id: str
    timestamp: datetime
    api_version: str


class ApiResponse[DataT](BaseModel):
    """The envelope for a successful API response."""

    status: ResponseStatus = ResponseStatus.SUCCESS
    data: DataT
    meta: ResponseMeta


class ErrorBody(BaseModel):
    """The structured error carried by an error response."""

    code: str
    message: str


class ApiErrorResponse(BaseModel):
    """The envelope for a failed API response."""

    status: ResponseStatus = ResponseStatus.ERROR
    error: ErrorBody
    meta: ResponseMeta


def _meta(context: RequestContext) -> ResponseMeta:
    return ResponseMeta(
        request_id=context.request_id,
        correlation_id=context.correlation_id,
        timestamp=datetime.now(UTC),
        api_version=API_VERSION,
    )


def build_success[DataT](data: DataT, context: RequestContext) -> ApiResponse[DataT]:
    """Wrap ``data`` in a successful response envelope."""

    return ApiResponse[DataT](data=data, meta=_meta(context))


def build_error(
    code: str, message: str, context: RequestContext
) -> ApiErrorResponse:
    """Build a structured error response envelope."""

    return ApiErrorResponse(
        error=ErrorBody(code=code, message=message), meta=_meta(context)
    )
