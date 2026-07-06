"""Shared helpers for the live Qdrant tests (ES-050).

Plain helper functions (no pytest fixtures). The ``live_qdrant`` suite is opt-in
and expects a reachable Qdrant published by the compose ``data`` profile on
``127.0.0.1:6333`` (``QDRANT_URL=http://127.0.0.1:6333``); in CI a service
container provides it. The connection comes from the standard ``QDRANT_*``
environment variables (``app.config.database.QdrantSettings``).
"""

import contextlib

from qdrant_client import AsyncQdrantClient

from app.config.database import QdrantSettings
from app.infrastructure.persistence.qdrant.client import create_client
from app.infrastructure.persistence.qdrant.memory_vector_store import (
    COLLECTION_NAME,
)


def live_qdrant_client() -> AsyncQdrantClient:
    """Create a Qdrant async client for the live vector store from the environment."""

    return create_client(QdrantSettings())


async def clear_collection(client: AsyncQdrantClient) -> None:
    """Drop the memory-embeddings collection so a test starts clean."""

    with contextlib.suppress(Exception):
        await client.delete_collection(COLLECTION_NAME)
