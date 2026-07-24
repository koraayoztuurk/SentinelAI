"""Domain tombstone transformations (data-lifecycle.md, ADR-017).

Erasure replaces a record with an explicit tombstone marker that preserves only
non-personal correlation structure — identifiers, timestamps and the owner/tenant
scope keys — and redacts personal content (data-lifecycle.md §4). These are pure
domain transformations: given a live domain object, each returns the tombstoned
object. Persistence adapters apply them; no I/O here.

Only the aggregates that carry personal free-text are transformed here — the
Investigation title, Evidence content/source, Trace summary, and Outcome
recommendation / conflicts / open questions. Findings and Reports hold only
structural references and metadata (no personal free-text), so they need no
redaction; the personal data they would expose lives in the evidence they
reference, which is redacted. Only the Investigation carries an end-of-life
timestamp (``erased_at``); its scoped objects follow it.
"""

from dataclasses import replace
from datetime import datetime

from app.domain.entity import Entity
from app.domain.enums import InvestigationStatus, MemoryStatus
from app.domain.evidence import Evidence
from app.domain.investigation import Investigation
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.memory_item import MemoryItem
from app.domain.trace import TraceEntry
from app.domain.value_objects import EvidenceSource

# The redaction marker replacing personal content in a tombstone. Non-blank so
# it satisfies the value objects' non-empty invariants; deliberately opaque.
REDACTED = "[erased]"


def tombstone_investigation(
    investigation: Investigation, erased_at: datetime
) -> Investigation:
    """Return the investigation as a tombstone (status ERASED, title redacted).

    Identifiers, ``created_at``, ``owner`` and ``tenant`` survive as correlation
    structure — the tombstone stays owner+tenant scoped so post-erasure
    authorization still resolves (ADR-017 §2).
    """

    return replace(
        investigation,
        title=REDACTED,
        status=InvestigationStatus.ERASED,
        erased_at=erased_at,
    )


def tombstone_evidence(evidence: Evidence) -> Evidence:
    """Return the evidence as a tombstone (content and source redacted).

    The integrity value (the content address, a SHA-256 hash) is retained as
    non-personal correlation structure so the payload bytes it names can be
    physically erased (ES-065).
    """

    return replace(evidence, content=REDACTED, source=EvidenceSource(REDACTED))


def tombstone_outcome(outcome: InvestigationOutcome) -> InvestigationOutcome:
    """Return the outcome as a tombstone (free-text fields redacted/cleared)."""

    return replace(
        outcome,
        recommendation=REDACTED,
        detected_conflicts=(),
        open_questions=(),
    )


def tombstone_trace_entry(entry: TraceEntry) -> TraceEntry:
    """Return the trace entry as a tombstone (summary redacted).

    The trace is append-only for business writes; erasure is the documented
    end-of-life exception (domain-model.md §11b / line 633, ADR-017 §4). Kind,
    actor, reference and timestamps survive as correlation structure.
    """

    return replace(entry, summary=REDACTED)


def tombstone_memory_item(item: MemoryItem) -> MemoryItem:
    """Return the Memory Item version as a tombstone (content redacted).

    Terminal ``ERASED`` status — distinct from ``DEPRECATED``, which controls
    relevance rather than existence (data-lifecycle.md §3). The identifiers,
    type, confidence, version, timestamps and the structural references survive;
    the knowledge text (the embedded content) is redacted. The derived embedding
    is deleted separately through the outbox projection (ADR-012/ADR-017 §5).
    """

    return replace(item, content=REDACTED, status=MemoryStatus.ERASED)


def tombstone_entity(entity: Entity) -> Entity:
    """Return the graph entity as a tombstone (identifying data redacted).

    The person-linked payload — ``display_name``, ``aliases`` and the
    descriptive ``attributes`` — is redacted; the stable identifier, type,
    confidence and provenance survive as correlation structure so relationships
    referencing the entity still resolve to an explicit erased node (§8a).
    Relationships themselves carry only structural references (type, confidence,
    supporting evidence), so they need no redaction.
    """

    return replace(entity, display_name=REDACTED, attributes={}, aliases=())
