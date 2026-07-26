"""Tests for readiness gating (ES-069, platform-observability §4).

Resolves the documented deviation where only PostgreSQL gated readiness. The
rule is ownership: a store holding data the platform is **authoritative** for
gates the verdict, a store holding a **derived** representation is reported but
never gates — gating on a derived store would turn a partial capability loss
into a total outage.

The registry is doubled so each store can be failed independently without
needing four real databases.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

pytestmark = pytest.mark.operational


class _Registry:
    """Persistence registry double whose probes fail on demand."""

    def __init__(self, *, unreachable: frozenset[str] = frozenset()) -> None:
        self._unreachable = unreachable

    async def ping_postgres(self) -> None:
        self._probe("postgres")

    async def ping_neo4j(self) -> None:
        self._probe("neo4j")

    async def ping_qdrant(self) -> None:
        self._probe("qdrant")

    def _probe(self, store: str) -> None:
        if store in self._unreachable:
            raise ConnectionError(f"{store} is unreachable")


def _client(*unreachable: str) -> TestClient:
    app = create_app()
    app.state.persistence = _Registry(unreachable=frozenset(unreachable))
    return TestClient(app)


def test_every_store_reachable_is_ready() -> None:
    response = _client().get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["postgres"] == body["neo4j"] == body["qdrant"] == "ok"


@pytest.mark.parametrize("store", ["postgres", "neo4j"])
def test_an_authoritative_store_gates_readiness(store: str) -> None:
    # PostgreSQL owns the Investigation family, Memory and audit; Neo4j owns
    # the Knowledge Graph (ES-048). A write to either has nowhere else to go,
    # so the unit cannot fulfil its business responsibility without it.
    response = _client(store).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_a_derived_store_is_reported_but_does_not_gate() -> None:
    # Qdrant holds embeddings reproducible from PostgreSQL (ADR-011/ADR-012),
    # and semantic retrieval already degrades to a contained failure.
    response = _client("qdrant").get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["qdrant"] == "unavailable"


def test_readiness_reports_every_store_truthfully_even_when_gating() -> None:
    # An operator must be able to see *which* dependency is down, not merely
    # that the unit is out of rotation.
    body = _client("postgres", "qdrant").get("/health/ready").json()

    assert body["postgres"] == "unavailable"
    assert body["qdrant"] == "unavailable"
    assert body["neo4j"] == "ok"


def test_readiness_before_startup_is_not_ready() -> None:
    # No lifespan: the registry does not exist, so nothing has been probed.
    body = TestClient(create_app()).get("/health/ready").json()

    assert body["status"] == "not_ready"
    assert body["postgres"] == "not_initialized"
