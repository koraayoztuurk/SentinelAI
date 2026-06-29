"""Planner Agent Investigation State.

The application/AI-layer operational view the Planner Agent reasons over
(planner-agent §4). It reuses the ES-003 typed domain value objects (typed
identifiers and ``Confidence``) to preserve the ubiquitous language and type
safety, while remaining an application/AI-layer structure — it is **not** a domain
object and is **consumed already-assembled** (the agent never assembles it).
"""

from dataclasses import dataclass

from app.domain.identifiers import EvidenceId, FindingId, InvestigationId, TaskId
from app.domain.value_objects import Confidence


@dataclass(frozen=True, slots=True)
class InvestigationState:
    """An already-assembled snapshot of an active investigation, for planning."""

    investigation_id: InvestigationId
    status: str
    confidence: Confidence
    objectives: tuple[str, ...] = ()
    evidence_ids: tuple[EvidenceId, ...] = ()
    finding_ids: tuple[FindingId, ...] = ()
    completed_tasks: tuple[TaskId, ...] = ()
    pending_tasks: tuple[TaskId, ...] = ()
    skipped_tasks: tuple[TaskId, ...] = ()
    history: tuple[str, ...] = ()
