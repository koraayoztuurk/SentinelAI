"""Typed identifier value objects.

Every domain object exposes a unique identifier. Rather than a single shared
string type, each object has its own identifier type so that the type checker
prevents passing, for example, an :class:`EvidenceId` where a :class:`FindingId`
is expected, and so that cross-object references remain self-documenting.

Each identifier is an immutable value wrapping a non-empty string. The domain
does not generate identifier values; callers supply them (identifier generation
is an infrastructure concern).

Each identifier is written as an explicit, standalone class. The small amount of
duplication is intentional: it is preferred over an early shared abstraction.
"""

from dataclasses import dataclass

from app.domain.exceptions import BlankValueError


@dataclass(frozen=True, slots=True)
class InvestigationId:
    """Unique identifier of an Investigation."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("InvestigationId must not be blank.")


@dataclass(frozen=True, slots=True)
class EvidenceId:
    """Unique identifier of an Evidence item."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("EvidenceId must not be blank.")


@dataclass(frozen=True, slots=True)
class FindingId:
    """Unique identifier of a Finding."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("FindingId must not be blank.")


@dataclass(frozen=True, slots=True)
class EntityId:
    """Globally unique, stable identifier of an Entity (Domain Rule 3)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("EntityId must not be blank.")


@dataclass(frozen=True, slots=True)
class RelationshipId:
    """Unique identifier of a Relationship."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("RelationshipId must not be blank.")


@dataclass(frozen=True, slots=True)
class TaskId:
    """Unique identifier of a Task."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("TaskId must not be blank.")


@dataclass(frozen=True, slots=True)
class MemoryItemId:
    """Unique identifier of a Memory Item."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("MemoryItemId must not be blank.")


@dataclass(frozen=True, slots=True)
class InvestigationOutcomeId:
    """Unique identifier of an Investigation Outcome."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("InvestigationOutcomeId must not be blank.")


@dataclass(frozen=True, slots=True)
class ReportId:
    """Unique identifier of a Report."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("ReportId must not be blank.")
