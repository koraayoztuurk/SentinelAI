"""Orchestration tracing ports.

The AI Runtime compositions record every decision and execution step into the
Investigation Trace — the explainability journal owned by the Investigation
Service (domain-model §11b, audit finding M-01/E-07). These ports keep the
compositions decoupled and caller-supplied:

- ``IdSource`` supplies identifiers (the platform generates no ids inside
  services or compositions).
- ``Clock`` supplies timestamps (no clock reads inside the domain or services;
  compositions receive time through this seam for the same reason).
- ``TraceSink`` receives trace entries; the production implementation is the
  Investigation Service's ``record_trace`` operation (AI → Application service
  interface, ADR-010).

Trace recording is **best-effort** inside compositions: a sink failure is
logged and never interrupts the investigation (mirroring the audit middleware's
containment stance) — the trace explains the investigation, it must not be able
to break it.
"""

import logging
from datetime import datetime
from typing import Protocol

from app.domain.trace import TraceEntry

logger = logging.getLogger(__name__)


class IdSource(Protocol):
    """Caller-supplied source of unique identifiers."""

    def new_id(self) -> str: ...


class Clock(Protocol):
    """Caller-supplied source of timestamps."""

    def now(self) -> datetime: ...


class TraceSink(Protocol):
    """Receives Investigation Trace entries (append-only)."""

    async def record_trace(self, entry: TraceEntry) -> TraceEntry: ...


async def record_best_effort(sink: TraceSink, entry: TraceEntry) -> None:
    """Record a trace entry, containing any sink failure (never raises)."""

    try:
        await sink.record_trace(entry)
    except Exception:  # best-effort: the trace must never break the flow
        logger.exception(
            "trace recording failed investigation_id=%s kind=%s",
            entry.investigation_id.value,
            entry.kind.value,
        )
