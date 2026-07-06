"""Domain ↔ ORM mappers for the Memory Item.

Pure conversion functions between the technology-independent
:class:`~app.domain.memory_item.MemoryItem` and its PostgreSQL row class,
mirroring the Investigation-family mappers. No session access, no I/O.
"""

from app.domain.enums import MemoryStatus
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    MemoryItemId,
    RelationshipId,
)
from app.domain.memory_item import MemoryItem
from app.domain.value_objects import Confidence, MemoryType
from app.infrastructure.persistence.postgres.memory.orm import MemoryItemRow


def memory_item_to_row(memory_item: MemoryItem) -> MemoryItemRow:
    return MemoryItemRow(
        id=memory_item.id.value,
        version=memory_item.version,
        type=memory_item.type.value,
        source_investigation_id=memory_item.source_investigation_id.value,
        confidence=memory_item.confidence.value,
        status=memory_item.status.value,
        created_at=memory_item.created_at,
        content=memory_item.content,
        supporting_evidence=[e.value for e in memory_item.supporting_evidence],
        referenced_findings=[f.value for f in memory_item.referenced_findings],
        referenced_entities=[e.value for e in memory_item.referenced_entities],
        referenced_relationships=[
            r.value for r in memory_item.referenced_relationships
        ],
    )


def memory_item_to_domain(row: MemoryItemRow) -> MemoryItem:
    return MemoryItem(
        id=MemoryItemId(row.id),
        type=MemoryType(row.type),
        source_investigation_id=InvestigationId(row.source_investigation_id),
        confidence=Confidence(row.confidence),
        status=MemoryStatus(row.status),
        created_at=row.created_at,
        version=row.version,
        content=row.content,
        supporting_evidence=tuple(
            EvidenceId(v) for v in row.supporting_evidence
        ),
        referenced_findings=tuple(FindingId(v) for v in row.referenced_findings),
        referenced_entities=tuple(EntityId(v) for v in row.referenced_entities),
        referenced_relationships=tuple(
            RelationshipId(v) for v in row.referenced_relationships
        ),
    )
