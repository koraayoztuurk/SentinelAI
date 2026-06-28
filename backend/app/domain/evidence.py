"""Evidence entity.

Evidence represents raw information collected during an investigation. It records
facts rather than conclusions and is immutable (Domain Rule 1): corrections are
represented as additional evidence rather than edits. Immutability is enforced by
modeling Evidence as a frozen dataclass.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.identifiers import EvidenceId, InvestigationId
from app.domain.value_objects import EvidenceIntegrity, EvidenceSource


@dataclass(frozen=True, slots=True)
class Evidence:
    """An immutable item of raw evidence belonging to an investigation."""

    id: EvidenceId
    investigation_id: InvestigationId
    source: EvidenceSource
    timestamp: datetime
    integrity: EvidenceIntegrity
    content: str
