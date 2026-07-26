"""Memory embedding outbox contract (ADR-012, ES-050; hardened in ES-067).

The transactional outbox records the **intent to derive** a Memory Item
embedding. A record is written in the same local transaction as the Memory Item
(so no request path writes to two stores — AC-14); the asynchronous, idempotent
projector consumes the pending records and produces the derived embedding.

This module defines the application-layer read/mark contract the **projector**
depends on (owned by the Memory Service's layer, ADR-004). The transactional
*write* of an outbox record happens inside the Memory Item persistence adapter
(same session), so it is not part of this port — the projector never writes new
intents, it only drains them.

Failure handling (ES-067) closes the ES-050 deferral "a failed record stays
``failed`` and is not auto-retried by the loop". A failure is now one of two
explicit outcomes:

- **retry** — the record stays pending with an incremented attempt count and a
  store-computed earliest next attempt, so repeated failures back off instead
  of spinning every poll interval;
- **dead-letter** — the retry budget is spent. The record leaves the working
  set into a terminal, *observable* state. Dead-lettering is deliberately
  visible rather than silent: the derived representation is missing and an
  operator has to know (ADR-012 keeps the authoritative Memory Item intact
  either way, so nothing is lost — only the embedding is absent).

The delay is decided by the projector's policy but **applied by the adapter**,
which owns the clock: services and the domain never read time (caller-supplies-
timestamps), so the port passes a relative ``delay_seconds`` rather than an
absolute timestamp.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class OutboxStatus(Enum):
    """Lifecycle of an outbox record.

    ``PENDING`` covers both a fresh record and one waiting out its retry
    backoff — the difference is the record's next-attempt time, not its state.
    ``DEAD_LETTER`` is terminal: the projector will not pick it up again.
    """

    PENDING = "pending"
    PROCESSED = "processed"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True, slots=True)
class OutboxRecord:
    """One pending derivation intent for a Memory Item version.

    ``seq`` is the store-generated identifier and append-order key. The record
    carries only identifiers — the projector reads the current Memory Item to
    obtain the text to embed (the outbox never snapshots the content).
    ``attempts`` is how many times projection has already failed for this
    record; the projector's retry policy reads it to decide retry vs
    dead-letter.
    """

    seq: int
    memory_id: str
    memory_version: int
    attempts: int = 0


class OutboxRepository(Protocol):
    """Read/mark operations the embedding projector depends on."""

    async def list_due(self, limit: int) -> tuple[OutboxRecord, ...]:
        """Pending records whose next attempt is due, oldest first.

        A record still waiting out its backoff is not due and is skipped;
        dead-lettered and processed records are never returned.
        """
        ...

    async def mark_processed(self, seq: int) -> None: ...

    async def mark_retry(
        self, seq: int, error: str, delay_seconds: float
    ) -> None:
        """Record a failed attempt and schedule the next one after the delay."""
        ...

    async def mark_dead_letter(self, seq: int, error: str) -> None:
        """Retire a record whose retry budget is spent (terminal, observable)."""
        ...
