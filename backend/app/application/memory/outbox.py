"""Memory embedding outbox contract (ADR-012, ES-050).

The transactional outbox records the **intent to derive** a Memory Item
embedding. A record is written in the same local transaction as the Memory Item
(so no request path writes to two stores — AC-14); the asynchronous, idempotent
projector consumes the pending records and produces the derived embedding.

This module defines the application-layer read/mark contract the **projector**
depends on (owned by the Memory Service's layer, ADR-004). The transactional
*write* of an outbox record happens inside the Memory Item persistence adapter
(same session), so it is not part of this port — the projector never writes new
intents, it only drains them.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class OutboxStatus(Enum):
    """Lifecycle of an outbox record."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class OutboxRecord:
    """One pending derivation intent for a Memory Item version.

    ``seq`` is the store-generated identifier and append-order key. The record
    carries only identifiers — the projector reads the current Memory Item to
    obtain the text to embed (the outbox never snapshots the content).
    """

    seq: int
    memory_id: str
    memory_version: int


class OutboxRepository(Protocol):
    """Read/mark operations the embedding projector depends on."""

    async def list_pending(self, limit: int) -> tuple[OutboxRecord, ...]: ...

    async def mark_processed(self, seq: int) -> None: ...

    async def mark_failed(self, seq: int, error: str) -> None: ...
