"""Domain lifecycle enumerations.

These enumerations define the observable lifecycle states of the domain objects
that have a documented set of states (domain-model.md v1.1.0). They are value
sets only: validation of permitted state transitions is a business-workflow
concern owned by the relevant backend service, not by the domain model.
"""

from enum import Enum


class InvestigationStatus(Enum):
    """Lifecycle states of an Investigation."""

    CREATED = "created"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class FindingStatus(Enum):
    """Lifecycle states of a Finding."""

    PROPOSED = "proposed"
    VALIDATED = "validated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class TaskStatus(Enum):
    """Execution states of a Task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class MemoryStatus(Enum):
    """Lifecycle states of a Memory Item."""

    CANDIDATE = "candidate"
    VERIFIED = "verified"
    ORGANIZATIONAL = "organizational"
    DEPRECATED = "deprecated"


class InvestigationOutcomeStatus(Enum):
    """Lifecycle states of an Investigation Outcome."""

    SYNTHESIZED = "synthesized"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    ESCALATED = "escalated"
