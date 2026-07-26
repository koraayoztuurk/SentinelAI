"""Tests for the Qdrant vector-store adapter's hardening (ES-067).

Closes the two ES-053 findings over a scripted client double (no live Qdrant):

- the **write** path used to leak raw driver errors, contained only by the
  background loop's broad catch, so a failed projection could not be classified
  or retried deliberately;
- ``ensure_collection`` accepted a collection built for a different vector size,
  turning one configuration mistake into an endless stream of opaque per-record
  write failures (the live-test dim-3 vs app dim-768 collision).
"""

import asyncio
from collections.abc import Sequence
from typing import Any

import httpx
import pytest
from qdrant_client import models
from qdrant_client.http.exceptions import ApiException

from app.application.memory.errors import (
    MemoryVectorDimensionMismatchError,
    MemoryVectorStoreUnavailableError,
)
from app.infrastructure.persistence.qdrant.memory_vector_store import (
    QdrantMemoryVectorStore,
)


class _FakeClient:
    """Scripted stand-in for ``AsyncQdrantClient`` (only what the adapter uses)."""

    def __init__(
        self,
        exists: bool = False,
        dimensions: int | None = None,
        upsert_error: Exception | None = None,
        exists_error: Exception | None = None,
    ) -> None:
        self._exists = exists
        self._dimensions = dimensions
        self._upsert_error = upsert_error
        self._exists_error = exists_error
        self.created: list[int] = []
        self.upserts: list[str] = []

    async def collection_exists(self, collection_name: str) -> bool:
        if self._exists_error is not None:
            raise self._exists_error
        return self._exists

    async def get_collection(self, collection_name: str) -> Any:
        vectors: Any
        if self._dimensions is None:
            # An unrecognized shape (named vectors) — not evidence of anything.
            vectors = {"named": object()}
        else:
            vectors = models.VectorParams(
                size=self._dimensions, distance=models.Distance.COSINE
            )
        params = type("Params", (), {"vectors": vectors})()
        config = type("Config", (), {"params": params})()
        return type("Info", (), {"config": config})()

    async def create_collection(
        self, collection_name: str, vectors_config: models.VectorParams
    ) -> None:
        self.created.append(vectors_config.size)

    async def upsert(
        self, collection_name: str, points: Sequence[models.PointStruct]
    ) -> None:
        if self._upsert_error is not None:
            raise self._upsert_error
        self.upserts.append(str(points[0].id))


def _store(client: _FakeClient) -> QdrantMemoryVectorStore:
    return QdrantMemoryVectorStore(client)  # type: ignore[arg-type]


# ------------------------------------------------------- collection dimensions


def test_absent_collection_is_created_at_the_configured_dimension() -> None:
    client = _FakeClient(exists=False)

    asyncio.run(_store(client).ensure_collection(768))

    assert client.created == [768]


def test_matching_collection_is_accepted_unchanged() -> None:
    client = _FakeClient(exists=True, dimensions=768)

    asyncio.run(_store(client).ensure_collection(768))

    # Already correct: nothing is recreated (the data survives).
    assert client.created == []


def test_mismatched_collection_is_refused_explicitly() -> None:
    # The ES-053 collision: live tests left the collection at dim 3 on the same
    # instance the app uses at dim 768.
    client = _FakeClient(exists=True, dimensions=3)

    with pytest.raises(MemoryVectorDimensionMismatchError) as exc_info:
        asyncio.run(_store(client).ensure_collection(768))

    assert exc_info.value.code == "memory.vector_dimension_mismatch"
    # The message names both sizes so the operator can act without digging.
    assert "3" in exc_info.value.message
    assert "768" in exc_info.value.message


def test_unreadable_vector_config_does_not_block_startup() -> None:
    # An unrecognized configuration is not evidence of a mismatch; refusing on
    # "I cannot tell" would be a false failure.
    client = _FakeClient(exists=True, dimensions=None)

    asyncio.run(_store(client).ensure_collection(768))

    assert client.created == []


def test_unreachable_store_maps_to_the_stable_contract_on_ensure() -> None:
    client = _FakeClient(exists_error=httpx.ConnectError("refused"))

    with pytest.raises(MemoryVectorStoreUnavailableError) as exc_info:
        asyncio.run(_store(client).ensure_collection(768))

    assert exc_info.value.code == "memory.vector_store_unavailable"


# -------------------------------------------------------------- write path


def test_upsert_writes_a_single_deterministic_point() -> None:
    client = _FakeClient()

    asyncio.run(_store(client).upsert("m1", (0.1, 0.2), {"memory_id": "m1"}))
    asyncio.run(_store(client).upsert("m1", (0.3, 0.4), {"memory_id": "m1"}))

    # Same id twice: idempotence (ADR-012) survives the error mapping.
    assert len(client.upserts) == 2
    assert client.upserts[0] == client.upserts[1]


def test_driver_error_on_write_maps_to_the_stable_contract() -> None:
    # ES-053 finding: a dimension-mismatch 400 used to escape as a raw driver
    # exception, leaving the projector unable to classify the failure.
    client = _FakeClient(upsert_error=ApiException("400 vector dimension error"))

    with pytest.raises(MemoryVectorStoreUnavailableError) as exc_info:
        asyncio.run(_store(client).upsert("m1", (0.1,), {"memory_id": "m1"}))

    assert exc_info.value.code == "memory.vector_store_unavailable"


def test_transport_error_on_write_maps_to_the_stable_contract() -> None:
    client = _FakeClient(upsert_error=httpx.ConnectError("refused"))

    with pytest.raises(MemoryVectorStoreUnavailableError):
        asyncio.run(_store(client).upsert("m1", (0.1,), {"memory_id": "m1"}))


def test_write_errors_never_leak_the_raw_driver_exception() -> None:
    client = _FakeClient(upsert_error=ApiException("internal driver detail"))

    with pytest.raises(MemoryVectorStoreUnavailableError) as exc_info:
        asyncio.run(_store(client).upsert("m1", (0.1,), {"memory_id": "m1"}))

    assert "internal driver detail" not in exc_info.value.message
