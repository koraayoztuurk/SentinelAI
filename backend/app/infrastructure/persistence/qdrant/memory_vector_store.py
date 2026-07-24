"""Qdrant memory vector-store adapter (ES-050).

Implements the application-layer
:class:`~app.application.memory.MemoryVectorStore` port over the async Qdrant
client — the projector's only outbound seam to the vector store.

Idempotence (ADR-012): the Qdrant point id is deterministic — ``UUID5`` of the
Memory Item id — so re-projecting the same Memory Item **upserts the same
single point** (the latest embedding replaces any prior one). Cosine distance,
a caller-supplied vector dimension; the collection is created only if absent.
"""

import uuid
from collections.abc import Mapping

import httpx
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import ApiException

from app.application.memory.errors import MemoryVectorStoreUnavailableError
from app.application.memory.vector_store import MemoryVectorMatch

# Stable namespace so a Memory Item always maps to the same Qdrant point id.
_POINT_NAMESPACE = uuid.UUID("6f0d5c8e-2a4b-4c1d-9e3f-0a1b2c3d4e5f")

COLLECTION_NAME = "memory_embeddings"


def _point_id(memory_id: str) -> str:
    return str(uuid.uuid5(_POINT_NAMESPACE, memory_id))


class QdrantMemoryVectorStore:
    """``MemoryVectorStore`` adapter over Qdrant."""

    def __init__(self, client: AsyncQdrantClient) -> None:
        self._client = client

    async def ensure_collection(self, dimensions: int) -> None:
        if await self._client.collection_exists(COLLECTION_NAME):
            return
        await self._client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=dimensions, distance=models.Distance.COSINE
            ),
        )

    async def upsert(
        self,
        memory_id: str,
        vector: tuple[float, ...],
        payload: Mapping[str, object],
    ) -> None:
        await self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=_point_id(memory_id),
                    vector=list(vector),
                    payload=dict(payload),
                )
            ],
        )

    async def delete(self, memory_id: str) -> None:
        """Delete the Memory Item's single point (ES-065, erasure projection).

        Idempotent: the point id is the same deterministic UUID5 ``upsert``
        uses, and deleting an absent point — or an absent collection — is a
        no-op. Store unavailability maps to the stable
        ``memory.vector_store_unavailable`` contract like the read path, so the
        projector can leave the record pending instead of losing the intent.
        """

        try:
            if not await self._client.collection_exists(COLLECTION_NAME):
                return
            await self._client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.PointIdsList(
                    points=[_point_id(memory_id)]
                ),
            )
        except (ApiException, httpx.HTTPError, OSError) as exc:
            raise MemoryVectorStoreUnavailableError(
                "The memory vector store is unreachable."
            ) from exc

    async def search(
        self, vector: tuple[float, ...], limit: int
    ) -> tuple[MemoryVectorMatch, ...]:
        """Best-first cosine-similarity matches (ES-051 semantic retrieval).

        An absent collection means nothing has been projected yet — an empty
        result, never an error (the projector owns collection creation). An
        unreachable store maps to the stable
        ``memory.vector_store_unavailable`` contract (mirroring the Neo4j
        adapter's ``graph.store_unavailable``), never a leaked driver
        exception.
        """

        try:
            if not await self._client.collection_exists(COLLECTION_NAME):
                return ()
            response = await self._client.query_points(
                collection_name=COLLECTION_NAME,
                query=list(vector),
                limit=limit,
                with_payload=True,
            )
        except (ApiException, httpx.HTTPError, OSError) as exc:
            raise MemoryVectorStoreUnavailableError(
                "The memory vector store is unreachable."
            ) from exc
        matches: list[MemoryVectorMatch] = []
        for point in response.points:
            payload = point.payload or {}
            memory_id = payload.get("memory_id")
            if not isinstance(memory_id, str) or not memory_id:
                # A point without its identifying payload cannot be mapped back
                # to the system of record — skip it rather than fabricate.
                continue
            matches.append(
                MemoryVectorMatch(
                    memory_id=memory_id,
                    score=float(point.score),
                    payload=payload,
                )
            )
        return tuple(matches)
