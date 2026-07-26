"""Qdrant memory vector-store adapter (ES-050).

Implements the application-layer
:class:`~app.application.memory.MemoryVectorStore` port over the async Qdrant
client — the projector's only outbound seam to the vector store.

Idempotence (ADR-012): the Qdrant point id is deterministic — ``UUID5`` of the
Memory Item id — so re-projecting the same Memory Item **upserts the same
single point** (the latest embedding replaces any prior one). Cosine distance,
a caller-supplied vector dimension; the collection is created only if absent.

Error containment (ES-067): **every** operation maps driver-level failures to
the stable ``memory.vector_store_unavailable`` contract — the write path used to
leak raw driver exceptions (e.g. a dimension-mismatch 400), contained only by
the background loop's broad catch, so a failed projection could not be
classified. ``ensure_collection`` additionally refuses to use a collection built
for a different vector size (``memory.vector_dimension_mismatch``) rather than
letting every upsert fail one by one.
"""

import uuid
from collections.abc import Mapping

import httpx
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import ApiException

from app.application.memory.errors import (
    MemoryVectorDimensionMismatchError,
    MemoryVectorStoreUnavailableError,
)
from app.application.memory.vector_store import MemoryVectorMatch

# Stable namespace so a Memory Item always maps to the same Qdrant point id.
_POINT_NAMESPACE = uuid.UUID("6f0d5c8e-2a4b-4c1d-9e3f-0a1b2c3d4e5f")

COLLECTION_NAME = "memory_embeddings"


def _point_id(memory_id: str) -> str:
    return str(uuid.uuid5(_POINT_NAMESPACE, memory_id))


class QdrantMemoryVectorStore:
    """``MemoryVectorStore`` adapter over Qdrant.

    ``collection`` is overridable so the live suite can work in its own
    collection (ES-067). Before that, live tests shared ``memory_embeddings``
    with the running application and left it at their 3-dimensional test size,
    which then broke the application's 768-dimensional writes — the ES-053
    finding. The application always uses the default.
    """

    def __init__(
        self, client: AsyncQdrantClient, collection: str = COLLECTION_NAME
    ) -> None:
        self._client = client
        self._collection = collection

    async def ensure_collection(self, dimensions: int) -> None:
        """Create the collection, or verify an existing one still fits (ES-067).

        A collection created for a different vector size cannot hold this
        embedder's vectors. Refusing here turns that into one explicit,
        actionable failure instead of an endless stream of per-record write
        errors.
        """

        try:
            if await self._client.collection_exists(self._collection):
                self._require_dimensions(
                    await self._existing_dimensions(), dimensions
                )
                return
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=dimensions, distance=models.Distance.COSINE
                ),
            )
        except (ApiException, httpx.HTTPError, OSError) as exc:
            raise MemoryVectorStoreUnavailableError(
                "The memory vector store is unreachable."
            ) from exc

    async def _existing_dimensions(self) -> int | None:
        """The configured vector size of the existing collection, if readable.

        Returns ``None`` when the shape is not the single unnamed vector this
        adapter creates — an unrecognized configuration is not evidence of a
        mismatch, so it must not block startup.
        """

        info = await self._client.get_collection(self._collection)
        vectors = info.config.params.vectors
        if isinstance(vectors, models.VectorParams):
            return int(vectors.size)
        return None

    def _require_dimensions(self, existing: int | None, expected: int) -> None:
        if existing is not None and existing != expected:
            raise MemoryVectorDimensionMismatchError(
                f"Collection '{self._collection}' stores {existing}-dimensional "
                f"vectors but the configured embedder produces {expected}."
            )

    async def upsert(
        self,
        memory_id: str,
        vector: tuple[float, ...],
        payload: Mapping[str, object],
    ) -> None:
        try:
            await self._client.upsert(
                collection_name=self._collection,
                points=[
                    models.PointStruct(
                        id=_point_id(memory_id),
                        vector=list(vector),
                        payload=dict(payload),
                    )
                ],
            )
        except (ApiException, httpx.HTTPError, OSError) as exc:
            # ES-053 finding: the write path used to leak raw driver errors
            # (a dimension-mismatch 400 among them) into the projector's broad
            # catch. Mapping them keeps failures classifiable and retriable.
            raise MemoryVectorStoreUnavailableError(
                "The memory vector store rejected the embedding write."
            ) from exc

    async def delete(self, memory_id: str) -> None:
        """Delete the Memory Item's single point (ES-065, erasure projection).

        Idempotent: the point id is the same deterministic UUID5 ``upsert``
        uses, and deleting an absent point — or an absent collection — is a
        no-op. Store unavailability maps to the stable
        ``memory.vector_store_unavailable`` contract like the read path, so the
        projector can leave the record pending instead of losing the intent.
        """

        try:
            if not await self._client.collection_exists(self._collection):
                return
            await self._client.delete(
                collection_name=self._collection,
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
            if not await self._client.collection_exists(self._collection):
                return ()
            response = await self._client.query_points(
                collection_name=self._collection,
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
