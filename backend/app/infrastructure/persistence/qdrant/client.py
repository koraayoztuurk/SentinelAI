"""Qdrant async client lifecycle.

Creates the Qdrant async client for the persistence foundation. The client is
created lazily, so application startup and unit tests do not require a live
vector database.
"""

from qdrant_client import AsyncQdrantClient

from app.config.database import QdrantSettings


def create_client(settings: QdrantSettings) -> AsyncQdrantClient:
    """Create the async Qdrant client for the given settings.

    ``check_compatibility`` is disabled so that constructing the client performs
    no network call; connections are opened lazily on first use.
    """

    return AsyncQdrantClient(url=settings.url, check_compatibility=False)
