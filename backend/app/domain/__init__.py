"""Domain layer.

Holds the technology-independent SentinelAI domain model (ES-003): the core
business objects defined by the Domain Model architecture document, together with
their identifiers, value objects, lifecycle enumerations and exceptions.

This layer depends only on the Python standard library and the shared-kernel base
exception (:class:`app.shared.exceptions.SentinelAIError`). It has no dependency
on other application layers, frameworks or storage technologies. Objects reference
each other by typed identifier rather than by embedding, preserving the service
ownership boundaries defined in ADR-004.

The names below are re-exported so consumers can import them directly from
``app.domain`` (for example ``from app.domain import Investigation, Confidence``).
"""

from app.domain.entity import Entity as Entity
from app.domain.enums import FindingStatus as FindingStatus
from app.domain.enums import InvestigationOutcomeStatus as InvestigationOutcomeStatus
from app.domain.enums import InvestigationStatus as InvestigationStatus
from app.domain.enums import MemoryStatus as MemoryStatus
from app.domain.enums import TaskStatus as TaskStatus
from app.domain.evidence import Evidence as Evidence
from app.domain.exceptions import BlankValueError as BlankValueError
from app.domain.exceptions import DomainError as DomainError
from app.domain.exceptions import InvalidConfidenceError as InvalidConfidenceError
from app.domain.exceptions import (
    MissingSupportingEvidenceError as MissingSupportingEvidenceError,
)
from app.domain.finding import Finding as Finding
from app.domain.identifiers import EntityId as EntityId
from app.domain.identifiers import EvidenceId as EvidenceId
from app.domain.identifiers import FindingId as FindingId
from app.domain.identifiers import InvestigationId as InvestigationId
from app.domain.identifiers import InvestigationOutcomeId as InvestigationOutcomeId
from app.domain.identifiers import MemoryItemId as MemoryItemId
from app.domain.identifiers import RelationshipId as RelationshipId
from app.domain.identifiers import ReportId as ReportId
from app.domain.identifiers import TaskId as TaskId
from app.domain.identifiers import TraceEntryId as TraceEntryId
from app.domain.investigation import Investigation as Investigation
from app.domain.investigation_outcome import (
    InvestigationOutcome as InvestigationOutcome,
)
from app.domain.memory_item import MemoryItem as MemoryItem
from app.domain.relationship import Relationship as Relationship
from app.domain.report import Report as Report
from app.domain.task import Task as Task
from app.domain.trace import TraceEntry as TraceEntry
from app.domain.trace import TraceEntryKind as TraceEntryKind
from app.domain.value_objects import ActorRef as ActorRef
from app.domain.value_objects import Confidence as Confidence
from app.domain.value_objects import EntityType as EntityType
from app.domain.value_objects import EvidenceIntegrity as EvidenceIntegrity
from app.domain.value_objects import EvidenceSource as EvidenceSource
from app.domain.value_objects import MemoryType as MemoryType
from app.domain.value_objects import Priority as Priority
from app.domain.value_objects import RelationshipType as RelationshipType
