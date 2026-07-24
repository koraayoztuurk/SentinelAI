"""Domain lifecycle enumerations.

These enumerations define the observable lifecycle states of the domain objects
that have a documented set of states (domain-model.md v1.1.0). They are value
sets only: validation of permitted state transitions is a business-workflow
concern owned by the relevant backend service, not by the domain model.
"""

from enum import Enum


class InvestigationStatus(Enum):
    """Lifecycle states of an Investigation.

    ``ERASED`` is the terminal end-of-life state (data-lifecycle.md, ADR-017):
    it is orthogonal to the business transitions above — an investigation may be
    erased from any state — and admits no further business write or transition.
    """

    CREATED = "created"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ERASED = "erased"


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
    """Lifecycle states of a Memory Item.

    ``DEPRECATED`` controls *relevance* (retrieval-invisible knowledge);
    ``ERASED`` is the terminal *end-of-life* state (data-lifecycle.md §3
    "deprecation is not deletion", ADR-017): its content is redacted and its
    derived embedding is deleted through the outbox projection.
    """

    CANDIDATE = "candidate"
    VERIFIED = "verified"
    ORGANIZATIONAL = "organizational"
    DEPRECATED = "deprecated"
    ERASED = "erased"


class InvestigationOutcomeStatus(Enum):
    """Lifecycle states of an Investigation Outcome."""

    SYNTHESIZED = "synthesized"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    ESCALATED = "escalated"
