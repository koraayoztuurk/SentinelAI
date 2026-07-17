"""Tests for the evidence payload API (ES-060, ADR-015).

Exercises the payload sub-resource end to end over in-memory doubles: raw
byte-stream upload (size-bounded, enveloped address result), attach with the
returned address, verified byte-stream download, and the stable error codes
(413 over the bound, 422 empty/broken reference, 404 for inline-only or
dangling payloads, 409 on verification mismatch).
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.application.investigation import InvestigationService, payload_address
from app.config.database import get_evidence_payload_settings
from app.main import create_app
from app.presentation.api.authorization import require_authorization
from app.presentation.api.generation import get_clock, get_id_generator
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from tests.support.doubles import (
    InMemoryEvidencePayloadStore,
    InMemoryEvidenceRepository,
    InMemoryFindingRepository,
    InMemoryInvestigationRepository,
    InMemoryOutcomeRepository,
    InMemoryReportRepository,
    InMemoryTraceRepository,
)

_FIXED_TIME = datetime(2026, 7, 17, tzinfo=UTC)
_CONTENT = b"raw log archive bytes"


class _CountingIds:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"id-{self._n}"


class _FixedClock:
    def now(self) -> datetime:
        return _FIXED_TIME


def _client(store: InMemoryEvidencePayloadStore | None = None) -> TestClient:
    app = create_app()
    service = InvestigationService(
        InMemoryInvestigationRepository(),
        InMemoryEvidenceRepository(),
        InMemoryFindingRepository(),
        InMemoryReportRepository(),
        InMemoryOutcomeRepository(),
        InMemoryTraceRepository(),
        payloads=store if store is not None else InMemoryEvidencePayloadStore(),
    )
    ids = _CountingIds()
    clock = _FixedClock()
    app.dependency_overrides[get_investigation_service] = lambda: service
    app.dependency_overrides[get_id_generator] = lambda: ids
    app.dependency_overrides[get_clock] = lambda: clock
    app.dependency_overrides[require_authorization] = lambda: None
    return TestClient(app)


def _create_investigation(client: TestClient) -> str:
    response = client.post(
        "/api/v1/investigations",
        json={"title": "Ingestion", "owner": "analyst-1", "priority": "high"},
    )
    assert response.status_code == 201
    investigation_id = response.json()["data"]["id"]
    assert isinstance(investigation_id, str)
    return investigation_id


def _upload(client: TestClient, investigation_id: str) -> str:
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence/payloads",
        content=_CONTENT,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 201
    address = response.json()["data"]["address"]
    assert isinstance(address, str)
    return address


def _attach(client: TestClient, investigation_id: str, integrity: str) -> str:
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"source": "upload", "integrity": integrity, "content": "raw log"},
    )
    assert response.status_code == 201
    evidence_id = response.json()["data"]["id"]
    assert isinstance(evidence_id, str)
    return evidence_id


# ----------------------------------------------------------------------- happy


def test_upload_attach_download_roundtrip() -> None:
    client = _client()
    investigation_id = _create_investigation(client)

    address = _upload(client, investigation_id)
    assert address == payload_address(_CONTENT)

    evidence_id = _attach(client, investigation_id, address)

    download = client.get(
        f"/api/v1/investigations/{investigation_id}"
        f"/evidence/{evidence_id}/payload"
    )
    assert download.status_code == 200
    assert download.content == _CONTENT
    assert download.headers["content-type"] == "application/octet-stream"
    assert "attachment" in download.headers["content-disposition"]


def test_upload_is_idempotent_and_reports_size() -> None:
    client = _client()
    investigation_id = _create_investigation(client)

    first = _upload(client, investigation_id)
    second = _upload(client, investigation_id)

    assert first == second
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence/payloads",
        content=_CONTENT,
    )
    assert response.json()["data"]["size_bytes"] == len(_CONTENT)


# ---------------------------------------------------------------------- errors


def test_upload_to_unknown_investigation_is_404() -> None:
    client = _client()
    response = client.post(
        "/api/v1/investigations/ghost/evidence/payloads", content=_CONTENT
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "investigation.not_found"


def test_upload_empty_body_is_422() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence/payloads",
        content=b"",
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "api.invalid_payload"


def test_upload_over_the_bound_is_413() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    too_large = b"x" * (get_evidence_payload_settings().max_bytes + 1)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence/payloads",
        content=too_large,
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "api.payload_too_large"


def test_attach_with_unstored_address_is_422() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={
            "source": "upload",
            "integrity": payload_address(b"never stored"),
            "content": "raw log",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == (
        "investigation.evidence_payload_missing"
    )


def test_download_for_inline_evidence_is_404() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    evidence_id = _attach(client, investigation_id, "verified")

    response = client.get(
        f"/api/v1/investigations/{investigation_id}"
        f"/evidence/{evidence_id}/payload"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == (
        "investigation.evidence_payload_not_found"
    )


def test_download_verification_mismatch_is_409() -> None:
    store = InMemoryEvidencePayloadStore()
    client = _client(store)
    investigation_id = _create_investigation(client)
    address = _upload(client, investigation_id)
    evidence_id = _attach(client, investigation_id, address)
    store.corrupt(address, b"tampered")

    response = client.get(
        f"/api/v1/investigations/{investigation_id}"
        f"/evidence/{evidence_id}/payload"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "investigation.evidence_payload_integrity"
    )


def test_download_across_investigations_is_404() -> None:
    client = _client()
    investigation_a = _create_investigation(client)
    investigation_b = _create_investigation(client)
    address = _upload(client, investigation_a)
    evidence_id = _attach(client, investigation_a, address)

    response = client.get(
        f"/api/v1/investigations/{investigation_b}"
        f"/evidence/{evidence_id}/payload"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == (
        "investigation.evidence_not_found"
    )
