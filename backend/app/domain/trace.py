"""Trace Entry entity.

A TraceEntry is one append-only record of the Investigation Trace — the
explainability journal of an investigation (domain-model.md §11b, ADR
provenance: audit finding M-01/E-07). It records who (which agent or component)
did or decided what, when, and under which correlation reference, so that every
AI-assisted step remains reconstructable by the analyst.

Trace entries are immutable and are only ever appended; the trace is distinct
from the security audit log (audit-and-observability.md): audit records
security-relevant access, the trace records investigation reasoning and
execution.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.domain.identifiers import InvestigationId, TraceEntryId
from app.domain.value_objects import ActorRef


class TraceEntryKind(Enum):
    """The category of a trace entry (fixed vocabulary)."""

    PLANNER_DECISION = "planner_decision"
    ACTION_EXECUTION = "action_execution"
    RETRIEVAL = "retrieval"
    LOOP_OUTCOME = "loop_outcome"
    ANALYST_NOTE = "analyst_note"


@dataclass(frozen=True, slots=True)
class TraceEntry:
    """An immutable, append-only entry of the Investigation Trace.

    ``actor`` records the component or person the entry originates from (for
    example ``planner-agent``); ``reference`` carries the correlating identifier
    of the traced step (an action id, a retrieval plan id); ``summary`` is the
    human-readable explanation of what happened or was decided.
    """

    id: TraceEntryId
    investigation_id: InvestigationId
    kind: TraceEntryKind
    actor: ActorRef
    summary: str
    reference: str
    created_at: datetime
