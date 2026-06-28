"""Domain value objects.

Value objects are immutable, self-validating descriptors used by the domain
entities. Each is an explicit, standalone frozen dataclass with its own
validation; the small duplication is intentional and preferred over an early
shared abstraction.

The "type"-style value objects (:class:`EntityType`, :class:`RelationshipType`,
:class:`MemoryType`, :class:`EvidenceSource`) and :class:`Priority` are
deliberately open vocabularies: the documentation presents their values as
non-exhaustive examples, so they wrap a validated string rather than enumerating
a fixed, closed set.
"""

from dataclasses import dataclass

from app.domain.exceptions import BlankValueError, InvalidConfidenceError


@dataclass(frozen=True, slots=True)
class Confidence:
    """A confidence estimate as a float in the inclusive range [0.0, 1.0]."""

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise InvalidConfidenceError(
                "Confidence must be within the inclusive range [0.0, 1.0]."
            )


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """The origin of an Evidence item (open vocabulary, e.g. a SIEM, DNS logs)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("EvidenceSource must not be blank.")


@dataclass(frozen=True, slots=True)
class EntityType:
    """The type of an Entity (open vocabulary, e.g. user, endpoint, domain)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("EntityType must not be blank.")


@dataclass(frozen=True, slots=True)
class RelationshipType:
    """The type of a Relationship (open vocabulary, e.g. authenticates_to)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("RelationshipType must not be blank.")


@dataclass(frozen=True, slots=True)
class MemoryType:
    """The type of a Memory Item (open vocabulary, e.g. attack pattern, playbook)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("MemoryType must not be blank.")


@dataclass(frozen=True, slots=True)
class Priority:
    """The priority of an Investigation or Task.

    The documentation does not define a priority value set, so this is modeled as
    an open vocabulary rather than a fixed enumeration.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("Priority must not be blank.")


@dataclass(frozen=True, slots=True)
class ActorRef:
    """A reference to an actor (a human analyst or an AI agent).

    The domain model defines no User or Agent entity, so the owner, creator,
    author and assigned-agent fields reference actors through this value object.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("ActorRef must not be blank.")


@dataclass(frozen=True, slots=True)
class EvidenceIntegrity:
    """A verifiable integrity value for an Evidence item.

    The documentation requires that evidence integrity remain verifiable but does
    not prescribe a scheme, so this is kept implementation-agnostic: an opaque,
    non-empty value whose verification mechanism is defined elsewhere.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise BlankValueError("EvidenceIntegrity must not be blank.")
