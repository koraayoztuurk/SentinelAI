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

from qdrant_client import AsyncQdrantClient, models

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
