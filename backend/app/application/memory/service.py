"""Memory Service.

Application-layer system-of-record for organizational Memory Items (PostgreSQL is
authoritative). It orchestrates the domain model, depends on a repository port,
performs structural validation, and never performs AI reasoning or embedding
generation (memory-architecture §11: the Memory Service persists; the Memory
Agent proposes).

Scope: the authoritative Memory Item lifecycle. Embedding, semantic-retrieval and
synchronization operations depend on an embedding provider and are introduced by
the AI/RAG specifications.

Logging here is lightweight operational observability for state-changing events;
it is explicitly not an audit mechanism.
"""

import logging

from app.application.memory.errors import (
    DuplicateMemoryError,
    InvalidMemoryVersionError,
    MemoryNotFoundError,
)
from app.application.memory.repositories import MemoryRepository
from app.domain.enums import MemoryStatus
from app.domain.identifiers import MemoryItemId
from app.domain.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class MemoryService:
    """Manages the authoritative, versioned lifecycle of Memory Items."""

    def __init__(self, memory: MemoryRepository) -> None:
        self._memory = memory

    async def create(self, memory_item: MemoryItem) -> MemoryItem:
        """Persist a new Memory Item as its initial version."""

        if memory_item.version != 1:
            raise InvalidMemoryVersionError(
                "A new Memory Item must start at version 1."
            )
        if await self._memory.get(memory_item.id) is not None:
            raise DuplicateMemoryError(
                f"Memory Item '{memory_item.id.value}' already exists."
            )
        await self._memory.add(memory_item)
        logger.info(
            "memory created id=%s version=%s status=%s",
            memory_item.id.value,
            memory_item.version,
            memory_item.status.value,
        )
        return memory_item

    async def get(self, memory_id: MemoryItemId) -> MemoryItem:
        """Return the latest version of a Memory Item, or raise if unknown."""

        return await self._require_latest(memory_id)

    async def update(self, memory_item: MemoryItem) -> MemoryItem:
        """Supersede a Memory Item with a new sequential version.

        Appends a new version; previously persisted versions are never modified.
        """

        latest = await self._require_latest(memory_item.id)
        if memory_item.version != latest.version + 1:
            raise InvalidMemoryVersionError(
                f"Memory Item '{memory_item.id.value}' must supersede version "
                f"{latest.version} with version {latest.version + 1}."
            )
        await self._memory.add(memory_item)
        logger.info(
            "memory superseded id=%s version=%s",
            memory_item.id.value,
            memory_item.version,
        )
        return memory_item

    async def deprecate(self, memory_id: MemoryItemId) -> MemoryItem:
        """Mark the latest version of a Memory Item as deprecated.

        Only the status of the latest version changes; historical versions remain
        immutable.
        """

        latest = await self._require_latest(memory_id)
        latest.status = MemoryStatus.DEPRECATED
        await self._memory.update(latest)
        logger.info(
            "memory deprecated id=%s version=%s",
            latest.id.value,
            latest.version,
        )
        return latest

    async def get_history(
        self, memory_id: MemoryItemId
    ) -> tuple[MemoryItem, ...]:
        """Return every version of a Memory Item ordered by version, ascending."""

        await self._require_latest(memory_id)
        versions = await self._memory.list_versions(memory_id)
        return tuple(sorted(versions, key=lambda item: item.version))

    async def _require_latest(self, memory_id: MemoryItemId) -> MemoryItem:
        memory_item = await self._memory.get(memory_id)
        if memory_item is None:
            raise MemoryNotFoundError(
                f"Memory Item '{memory_id.value}' not found."
            )
        return memory_item
