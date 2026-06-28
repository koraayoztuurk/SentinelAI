"""Task entity.

A Task represents a unit of work performed during an investigation by an AI agent
or analyst. Tasks enable structured investigation planning and execution tracking
and may depend on the completion of other tasks, which they reference by identifier.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import TaskStatus
from app.domain.identifiers import InvestigationId, TaskId
from app.domain.value_objects import ActorRef, Priority


@dataclass(slots=True)
class Task:
    """A unit of investigation work with execution status and dependencies."""

    id: TaskId
    investigation_id: InvestigationId
    assigned_agent: ActorRef
    status: TaskStatus
    priority: Priority
    created_at: datetime
    dependencies: tuple[TaskId, ...] = ()
