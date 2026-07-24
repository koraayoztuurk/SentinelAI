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

from app.domain.identifiers import InvestigationId, MemoryItemId
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

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[MemoryItem, ...]:
        """Latest version of every Memory Item originating from the investigation.

        Cross-service reference by identifier only (database-architecture §8a):
        the investigation itself is never validated here, so an unknown
        identifier simply yields an empty result. Deterministic
        ``(created_at, id)`` ordering.
        """
        ...

    async def erase(self, memory_id: MemoryItemId) -> None:
        """Tombstone **every version** of a Memory Item (ES-065, ADR-017).

        End-of-life, distinct from deprecation: each version's knowledge text
        holds the personal content, so all of them are redacted and marked
        ``ERASED``. Records the derived-embedding erasure intent in the **same
        transaction** (the outbox, ADR-012), so the point deletion propagates
        asynchronously and no request path writes two stores (AC-14).
        """
        ...
