"""Tests for the Memory API (ES-017).

Each test builds a fresh app via ``create_app`` and overrides the service and the
id/clock generators with deterministic in-memory doubles, so real endpoints
(controllers, schemas, envelope and error translation) are exercised end to end
without a database. The in-memory repository tracks every version, letting the
tests assert the immutable-history guarantee.
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.application.memory import MemoryService
from app.domain.identifiers import MemoryItemId
from app.domain.memory_item import MemoryItem
from app.main import create_app
from app.presentation.api.generation import get_clock, get_id_generator
from app.presentation.api.v1.memory.dependencies import get_memory_service

_FIXED_TIME = datetime(2026, 6, 30, tzinfo=UTC)


# --------------------------------------------------------------- in-memory double


class _MemoryRepo:
    def __init__(self) -> None:
        self._versions: dict[str, list[MemoryItem]] = {}

    async def add(self, memory_item: MemoryItem) -> None:
        self._versions.setdefault(memory_item.id.value, []).append(memory_item)

    async def get(self, memory_id: MemoryItemId) -> MemoryItem | None:
        versions = self._versions.get(memory_id.value)
        if not versions:
            return None
        return max(versions, key=lambda item: item.version)

    async def update(self, memory_item: MemoryItem) -> None:
        versions = self._versions.setdefault(memory_item.id.value, [])
        for index, existing in enumerate(versions):
            if existing.version == memory_item.version:
                versions[index] = memory_item
                return
        versions.append(memory_item)

    async def list_versions(
        self, memory_id: MemoryItemId
    ) -> tuple[MemoryItem, ...]:
        return tuple(self._versions.get(memory_id.value, ()))


class _CountingIds:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"id-{self._n}"


class _FixedClock:
    def now(self) -> datetime:
        return _FIXED_TIME


def _client() -> TestClient:
    app = create_app()
    service = MemoryService(_MemoryRepo())
    app.dependency_overrides[get_memory_service] = lambda: service
    app.dependency_overrides[get_id_generator] = lambda: _CountingIds()
    app.dependency_overrides[get_clock] = lambda: _FixedClock()
    return TestClient(app)


def _create_payload(
    confidence: float = 0.5, status_value: str = "candidate"
) -> dict[str, object]:
    return {
        "type": "attack_pattern",
        "source_investigation_id": "inv-1",
        "confidence": confidence,
        "status": status_value,
    }


def _create(client: TestClient, **kwargs: object) -> str:
    response = client.post("/api/v1/memory", json=_create_payload(**kwargs))
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _update_payload(
    version: int, confidence: float = 0.9, status_value: str = "verified"
) -> dict[str, object]:
    return {
        "type": "attack_pattern",
        "source_investigation_id": "inv-1",
        "confidence": confidence,
        "status": status_value,
        "version": version,
        "created_at": "2026-06-30T00:00:00+00:00",
    }


# ------------------------------------------------------------------ create / get


def test_create_memory_envelope() -> None:
    response = _client().post("/api/v1/memory", json=_create_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["id"] == "id-1"
    assert body["data"]["version"] == 1
    assert body["data"]["status"] == "candidate"
    assert body["meta"]["request_id"] == response.headers.get("X-Request-ID")


def test_get_memory() -> None:
    client = _client()
    memory_id = _create(client)
    response = client.get(f"/api/v1/memory/{memory_id}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == memory_id


def test_get_missing_memory_returns_404() -> None:
    response = _client().get("/api/v1/memory/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "memory.not_found"


# ----------------------------------------------------------------------- update


def test_update_memory_supersedes_version() -> None:
    client = _client()
    memory_id = _create(client)
    response = client.put(
        f"/api/v1/memory/{memory_id}", json=_update_payload(version=2)
    )
    assert response.status_code == 200
    assert response.json()["data"]["version"] == 2
    assert response.json()["data"]["status"] == "verified"


def test_update_memory_wrong_version_returns_422() -> None:
    client = _client()
    memory_id = _create(client)
    response = client.put(
        f"/api/v1/memory/{memory_id}", json=_update_payload(version=5)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "memory.invalid_version"


# -------------------------------------------------------------------- deprecate


def test_deprecate_memory() -> None:
    client = _client()
    memory_id = _create(client)
    response = client.post(f"/api/v1/memory/{memory_id}/deprecate")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "deprecated"


# ----------------------------------------------------------------------- history


def test_history_returns_versions_ascending() -> None:
    client = _client()
    memory_id = _create(client)
    client.put(f"/api/v1/memory/{memory_id}", json=_update_payload(version=2))
    response = client.get(f"/api/v1/memory/{memory_id}/history")
    assert response.status_code == 200
    assert [item["version"] for item in response.json()["data"]] == [1, 2]


def test_history_preserves_immutable_version_one() -> None:
    client = _client()
    memory_id = _create(client, confidence=0.5, status_value="candidate")
    client.put(
        f"/api/v1/memory/{memory_id}",
        json=_update_payload(version=2, confidence=0.9, status_value="verified"),
    )
    history = client.get(f"/api/v1/memory/{memory_id}/history").json()["data"]
    assert len(history) == 2

    v1, v2 = history[0], history[1]
    # Version 1 remains unchanged after the update (ES-007 immutable history).
    assert v1["version"] == 1
    assert v1["confidence"] == 0.5
    assert v1["status"] == "candidate"
    # Version 2 reflects the update.
    assert v2["version"] == 2
    assert v2["confidence"] == 0.9
    assert v2["status"] == "verified"


# ----------------------------------------------------------------- not configured


def test_service_not_configured_returns_503() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/memory", json=_create_payload())
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "api.persistence_not_configured"
