"""Tests for the API foundation (ES-014).

Exercises the request-context middleware, the standard response/error envelopes and
the versioned router. A small in-test FastAPI app wires the real foundation pieces
with minimal routes, since resource endpoints are introduced by later
specifications.
"""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import __version__
from app.main import app as main_app
from app.presentation.api import API_VERSION
from app.presentation.api.context import (
    CORRELATION_ID_HEADER,
    PROCESS_TIME_HEADER,
    REQUEST_ID_HEADER,
    RequestContext,
    RequestContextMiddleware,
    get_request_context,
)
from app.presentation.api.response import (
    ApiResponse,
    ResponseStatus,
    build_success,
)
from app.presentation.api.v1 import api_v1_router
from app.presentation.exception_handlers import register_exception_handlers
from app.shared.exceptions import SentinelAIError


class _BoomError(SentinelAIError):
    code = "test.boom"


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    @app.get("/_success")
    def _success(
        context: RequestContext = Depends(get_request_context),
    ) -> ApiResponse[dict[str, str]]:
        return build_success({"hello": "world"}, context)

    @app.get("/_app_error")
    def _app_error() -> None:
        raise _BoomError("Something broke safely.")

    @app.get("/_unexpected")
    def _unexpected() -> None:
        raise RuntimeError("leaked internals")

    return app


# ----------------------------------------------------------------- middleware


def test_response_carries_request_id_header() -> None:
    client = TestClient(main_app)
    response = client.get("/health")
    assert response.headers.get(REQUEST_ID_HEADER)
    assert response.headers.get(PROCESS_TIME_HEADER) is not None


def test_correlation_id_is_echoed_when_provided() -> None:
    client = TestClient(main_app)
    response = client.get("/health", headers={CORRELATION_ID_HEADER: "corr-123"})
    assert response.headers.get(CORRELATION_ID_HEADER) == "corr-123"


def test_correlation_id_defaults_to_request_id_when_absent() -> None:
    client = TestClient(main_app)
    response = client.get("/health")
    assert (
        response.headers.get(CORRELATION_ID_HEADER)
        == response.headers.get(REQUEST_ID_HEADER)
    )


# ----------------------------------------------------------------- success envelope


def test_success_envelope_structure() -> None:
    client = TestClient(_build_test_app())
    response = client.get("/_success")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ResponseStatus.SUCCESS.value
    assert body["data"] == {"hello": "world"}
    assert body["meta"]["api_version"] == API_VERSION
    assert body["meta"]["request_id"] == response.headers.get(REQUEST_ID_HEADER)
    assert body["meta"]["timestamp"]


# ----------------------------------------------------------------- error envelope


def test_application_error_envelope() -> None:
    client = TestClient(_build_test_app())
    response = client.get("/_app_error")
    assert response.status_code == 400
    body = response.json()
    assert body["status"] == ResponseStatus.ERROR.value
    assert body["error"] == {
        "code": "test.boom",
        "message": "Something broke safely.",
    }
    assert body["meta"]["request_id"] == response.headers.get(REQUEST_ID_HEADER)


def test_unexpected_error_is_generic_with_request_id() -> None:
    client = TestClient(_build_test_app(), raise_server_exceptions=False)
    response = client.get("/_unexpected")
    assert response.status_code == 500
    body = response.json()
    assert body["status"] == ResponseStatus.ERROR.value
    assert body["error"]["code"] == "internal_server_error"
    assert "leaked internals" not in body["error"]["message"]
    assert body["meta"]["request_id"]


# ----------------------------------------------------------------- versioned router


def test_versioned_router_prefix() -> None:
    assert api_v1_router.prefix == "/api/v1"


def test_health_smoke_still_passes() -> None:
    client = TestClient(main_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == __version__
