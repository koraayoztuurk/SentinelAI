"""Repository contract required by the Memory Service.

Per-aggregate port for authoritative Memory Item persistence (PostgreSQL is the
system of record). It inherits the domain
:class:`~app.domain.repositories.Repository` marker and is implemented by the
infrastructure layer (the concrete PostgreSQL adapter is introduced by a later
specification). Defining it here keeps the domain model untouched while
preserving the inward dependency direction.

Memory Items are versioned: ``add`` appends a version, ``get`` returns the latest
version, ``list_versions`` returns every version, and ``update`` modifies an
existing version in place (used only for the latest-version status change in
deprecation). Embedding/Vector-Database operations are out of scope here and are
introduced with the AI/RAG specifications.
"""

from typing import Protocol

from app.domain.identifiers import MemoryItemId
from app.domain.memory_item import MemoryItem
from app.domain.repositories import Repository


class MemoryRepository(Repository, Protocol):
    """Authoritative persistence operations for versioned Memory Items."""

    async def add(self, memory_item: MemoryItem) -> None: ...

    async def get(self, memory_id: MemoryItemId) -> MemoryItem | None: ...

    async def update(self, memory_item: MemoryItem) -> None: ...

    async def list_versions(
        self, memory_id: MemoryItemId
    ) -> tuple[MemoryItem, ...]: ...
