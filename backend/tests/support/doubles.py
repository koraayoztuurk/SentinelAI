"""Shared in-memory test doubles (Test Foundation, ES-032).

Reusable, dict-backed repository doubles for the Investigation family plus
deterministic id/clock doubles, matching the repository/generation ports the
services and API depend on. They are plain classes (no pytest fixtures), so any
test can construct and wire them directly. This is common validation
infrastructure, not owned by a single domain.
"""

from datetime import datetime

from app.domain.entity import Entity
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    MemoryItemId,
    RelationshipId,
    ReportId,
)
from app.domain.investigation import Investigation
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.memory_item import MemoryItem
from app.domain.relationship import Relationship
from app.domain.report import Report
from app.domain.trace import TraceEntry

# ------------------------------------------------------------- repository doubles


class InMemoryInvestigationRepository:
    """Dict-backed Investigation repository double."""

    def __init__(self) -> None:
        self._items: dict[str, Investigation] = {}

    async def add(self, investigation: Investigation) -> None:
        self._items[investigation.id.value] = investigation

    async def get(self, investigation_id: InvestigationId) -> Investigation | None:
        return self._items.get(investigation_id.value)

    async def update(self, investigation: Investigation) -> None:
        self._items[investigation.id.value] = investigation


class InMemoryEvidenceRepository:
    """Dict-backed Evidence repository double."""

    def __init__(self) -> None:
        self._items: dict[str, Evidence] = {}

    async def add(self, evidence: Evidence) -> None:
        self._items[evidence.id.value] = evidence

    async def get(self, evidence_id: EvidenceId) -> Evidence | None:
        return self._items.get(evidence_id.value)

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Evidence, ...]:
        return tuple(
            e
            for e in self._items.values()
            if e.investigation_id == investigation_id
        )


class InMemoryFindingRepository:
    """Dict-backed Finding repository double."""

    def __init__(self) -> None:
        self._items: dict[str, Finding] = {}

    async def add(self, finding: Finding) -> None:
        self._items[finding.id.value] = finding

    async def get(self, finding_id: FindingId) -> Finding | None:
        return self._items.get(finding_id.value)

    async def update(self, finding: Finding) -> None:
        self._items[finding.id.value] = finding

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Finding, ...]:
        return tuple(
            f
            for f in self._items.values()
            if f.investigation_id == investigation_id
        )


class InMemoryReportRepository:
    """Dict-backed Report repository double."""

    def __init__(self) -> None:
        self._items: dict[str, Report] = {}

    async def add(self, report: Report) -> None:
        self._items[report.id.value] = report

    async def get(self, report_id: ReportId) -> Report | None:
        return self._items.get(report_id.value)

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Report, ...]:
        return tuple(
            r
            for r in self._items.values()
            if r.investigation_id == investigation_id
        )


class InMemoryOutcomeRepository:
    """Dict-backed InvestigationOutcome repository double (0..1 per investigation)."""

    def __init__(self) -> None:
        self._items: dict[str, InvestigationOutcome] = {}

    async def add(self, outcome: InvestigationOutcome) -> None:
        self._items[outcome.investigation_id.value] = outcome

    async def get_for_investigation(
        self, investigation_id: InvestigationId
    ) -> InvestigationOutcome | None:
        return self._items.get(investigation_id.value)


class InMemoryTraceRepository:
    """List-backed, append-only Investigation Trace repository double."""

    def __init__(self) -> None:
        self._entries: list[TraceEntry] = []

    async def add(self, entry: TraceEntry) -> None:
        self._entries.append(entry)

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[TraceEntry, ...]:
        return tuple(
            e for e in self._entries if e.investigation_id == investigation_id
        )


class InMemoryGraphRepository:
    """Dict-backed graph repository double (entities + relationships).

    ``neighbors`` implements a minimal single-hop adjacency: entities directly
    connected to the requested entity, bounded by ``max_nodes``. Documented
    traversal semantics belong to the Graph Service / Neo4j adapter.
    """

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}

    async def add_entity(self, entity: Entity) -> None:
        self._entities[entity.id.value] = entity

    async def get_entity(self, entity_id: EntityId) -> Entity | None:
        return self._entities.get(entity_id.value)

    async def update_entity(self, entity: Entity) -> None:
        self._entities[entity.id.value] = entity

    async def add_relationship(self, relationship: Relationship) -> None:
        self._relationships[relationship.id.value] = relationship

    async def get_relationship(
        self, relationship_id: RelationshipId
    ) -> Relationship | None:
        return self._relationships.get(relationship_id.value)

    async def update_relationship(self, relationship: Relationship) -> None:
        self._relationships[relationship.id.value] = relationship

    async def list_relationships_for_entity(
        self, entity_id: EntityId
    ) -> tuple[Relationship, ...]:
        return tuple(
            r
            for r in self._relationships.values()
            if entity_id in (r.source_entity_id, r.target_entity_id)
        )

    async def neighbors(
        self, entity_id: EntityId, depth: int, max_nodes: int
    ) -> tuple[Entity, ...]:
        result: list[Entity] = []
        for relationship in self._relationships.values():
            other: EntityId | None = None
            if relationship.source_entity_id == entity_id:
                other = relationship.target_entity_id
            elif relationship.target_entity_id == entity_id:
                other = relationship.source_entity_id
            if other is not None and other.value in self._entities:
                result.append(self._entities[other.value])
            if len(result) >= max_nodes:
                break
        return tuple(result)


class InMemoryMemoryRepository:
    """Dict-backed versioned MemoryItem repository double.

    ``add`` appends a version, ``get`` returns the latest version, ``update``
    replaces the matching version in place (deprecation), ``list_versions``
    returns every version ordered by version number ascending.
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[MemoryItem]] = {}

    async def add(self, memory_item: MemoryItem) -> None:
        self._versions.setdefault(memory_item.id.value, []).append(memory_item)

    async def get(self, memory_id: MemoryItemId) -> MemoryItem | None:
        versions = self._versions.get(memory_id.value)
        return max(versions, key=lambda m: m.version) if versions else None

    async def update(self, memory_item: MemoryItem) -> None:
        versions = self._versions.get(memory_item.id.value, [])
        for index, existing in enumerate(versions):
            if existing.version == memory_item.version:
                versions[index] = memory_item
                return

    async def list_versions(
        self, memory_id: MemoryItemId
    ) -> tuple[MemoryItem, ...]:
        return tuple(
            sorted(
                self._versions.get(memory_id.value, ()),
                key=lambda m: m.version,
            )
        )

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[MemoryItem, ...]:
        latest = (
            max(versions, key=lambda m: m.version)
            for versions in self._versions.values()
            if versions
        )
        matching = [
            item
            for item in latest
            if item.source_investigation_id == investigation_id
        ]
        return tuple(
            sorted(matching, key=lambda m: (m.created_at, m.id.value))
        )


# ------------------------------------------------------------ generation doubles


class SequentialIdGenerator:
    """Deterministic ``IdGenerator``: emits ``<prefix>-1``, ``<prefix>-2``, ..."""

    def __init__(self, prefix: str = "id") -> None:
        self._prefix = prefix
        self._counter = 0

    def new_id(self) -> str:
        self._counter += 1
        return f"{self._prefix}-{self._counter}"


class FixedClock:
    """Deterministic ``Clock``: always returns the same instant."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class InMemoryEvidencePayloadStore:
    """Dict-backed content-addressed evidence payload store double (ES-060)."""

    def __init__(self) -> None:
        self._payloads: dict[str, bytes] = {}

    async def put(self, address: str, content: bytes) -> None:
        self._payloads.setdefault(address, content)

    async def get(self, address: str) -> bytes | None:
        return self._payloads.get(address)

    async def exists(self, address: str) -> bool:
        return address in self._payloads

    def corrupt(self, address: str, content: bytes) -> None:
        """Overwrite a stored payload out of band (integrity-fault tests)."""

        self._payloads[address] = content

    def remove(self, address: str) -> None:
        """Drop a stored payload out of band (dangling-reference tests)."""

        self._payloads.pop(address, None)
