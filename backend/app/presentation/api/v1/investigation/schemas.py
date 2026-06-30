"""Investigation API request/response schemas and mappers.

The request models carry only the client-supplied business fields; the response
models are flat projections of the domain objects. All DTO-to-domain and
domain-to-DTO conversion lives here (``to_domain`` / ``from_domain``) so the
controllers stay thin (parse -> map -> service -> envelope). Generated identifiers
and timestamps are passed in by the controller from the API's ``IdGenerator`` and
``Clock``.
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import FindingStatus, InvestigationStatus
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    RelationshipId,
    ReportId,
)
from app.domain.investigation import Investigation
from app.domain.report import Report
from app.domain.value_objects import (
    ActorRef,
    Confidence,
    EvidenceIntegrity,
    EvidenceSource,
    Priority,
)

# --------------------------------------------------------------- investigation


class InvestigationCreateRequest(BaseModel):
    """Client-supplied fields for creating an investigation."""

    title: str
    owner: str
    priority: str

    def to_domain(self, *, id_value: str, created_at: datetime) -> Investigation:
        return Investigation(
            id=InvestigationId(id_value),
            title=self.title,
            status=InvestigationStatus.CREATED,
            created_at=created_at,
            owner=ActorRef(self.owner),
            priority=Priority(self.priority),
        )


class InvestigationStatusChangeRequest(BaseModel):
    """Target lifecycle status for an investigation transition."""

    status: InvestigationStatus


class InvestigationResponse(BaseModel):
    """Flat projection of an investigation."""

    id: str
    title: str
    status: str
    created_at: datetime
    owner: str
    priority: str

    @classmethod
    def from_domain(cls, investigation: Investigation) -> "InvestigationResponse":
        return cls(
            id=investigation.id.value,
            title=investigation.title,
            status=investigation.status.value,
            created_at=investigation.created_at,
            owner=investigation.owner.value,
            priority=investigation.priority.value,
        )


# -------------------------------------------------------------------- evidence


class EvidenceCreateRequest(BaseModel):
    """Client-supplied fields for attaching evidence."""

    source: str
    integrity: str
    content: str

    def to_domain(
        self,
        *,
        id_value: str,
        investigation_id_value: str,
        timestamp: datetime,
    ) -> Evidence:
        return Evidence(
            id=EvidenceId(id_value),
            investigation_id=InvestigationId(investigation_id_value),
            source=EvidenceSource(self.source),
            timestamp=timestamp,
            integrity=EvidenceIntegrity(self.integrity),
            content=self.content,
        )


class EvidenceResponse(BaseModel):
    """Flat projection of an evidence item."""

    id: str
    investigation_id: str
    source: str
    timestamp: datetime
    integrity: str
    content: str

    @classmethod
    def from_domain(cls, evidence: Evidence) -> "EvidenceResponse":
        return cls(
            id=evidence.id.value,
            investigation_id=evidence.investigation_id.value,
            source=evidence.source.value,
            timestamp=evidence.timestamp,
            integrity=evidence.integrity.value,
            content=evidence.content,
        )


# --------------------------------------------------------------------- finding


class FindingCreateRequest(BaseModel):
    """Client-supplied fields for creating a finding."""

    supporting_evidence: list[str]
    creator: str
    confidence: float
    status: FindingStatus
    related_entities: list[str] = []
    related_relationships: list[str] = []

    def to_domain(
        self,
        *,
        id_value: str,
        investigation_id_value: str,
        created_at: datetime,
    ) -> Finding:
        return Finding(
            id=FindingId(id_value),
            investigation_id=InvestigationId(investigation_id_value),
            supporting_evidence=tuple(
                EvidenceId(value) for value in self.supporting_evidence
            ),
            creator=ActorRef(self.creator),
            created_at=created_at,
            confidence=Confidence(self.confidence),
            status=self.status,
            related_entities=tuple(
                EntityId(value) for value in self.related_entities
            ),
            related_relationships=tuple(
                RelationshipId(value) for value in self.related_relationships
            ),
        )


class FindingUpdateRequest(BaseModel):
    """Full finding representation supplied on update (PUT semantics)."""

    supporting_evidence: list[str]
    creator: str
    created_at: datetime
    confidence: float
    status: FindingStatus
    related_entities: list[str] = []
    related_relationships: list[str] = []

    def to_domain(
        self, *, id_value: str, investigation_id_value: str
    ) -> Finding:
        return Finding(
            id=FindingId(id_value),
            investigation_id=InvestigationId(investigation_id_value),
            supporting_evidence=tuple(
                EvidenceId(value) for value in self.supporting_evidence
            ),
            creator=ActorRef(self.creator),
            created_at=self.created_at,
            confidence=Confidence(self.confidence),
            status=self.status,
            related_entities=tuple(
                EntityId(value) for value in self.related_entities
            ),
            related_relationships=tuple(
                RelationshipId(value) for value in self.related_relationships
            ),
        )


class FindingResponse(BaseModel):
    """Flat projection of a finding."""

    id: str
    investigation_id: str
    supporting_evidence: list[str]
    creator: str
    created_at: datetime
    confidence: float
    status: str
    related_entities: list[str]
    related_relationships: list[str]

    @classmethod
    def from_domain(cls, finding: Finding) -> "FindingResponse":
        return cls(
            id=finding.id.value,
            investigation_id=finding.investigation_id.value,
            supporting_evidence=[e.value for e in finding.supporting_evidence],
            creator=finding.creator.value,
            created_at=finding.created_at,
            confidence=finding.confidence.value,
            status=finding.status.value,
            related_entities=[e.value for e in finding.related_entities],
            related_relationships=[
                r.value for r in finding.related_relationships
            ],
        )


# ---------------------------------------------------------------------- report


class ReportCreateRequest(BaseModel):
    """Client-supplied fields for creating a report."""

    author: str
    version: int = 1

    def to_domain(
        self,
        *,
        id_value: str,
        investigation_id_value: str,
        created_at: datetime,
    ) -> Report:
        return Report(
            id=ReportId(id_value),
            investigation_id=InvestigationId(investigation_id_value),
            author=ActorRef(self.author),
            created_at=created_at,
            version=self.version,
        )


class ReportResponse(BaseModel):
    """Flat projection of a report."""

    id: str
    investigation_id: str
    author: str
    created_at: datetime
    version: int

    @classmethod
    def from_domain(cls, report: Report) -> "ReportResponse":
        return cls(
            id=report.id.value,
            investigation_id=report.investigation_id.value,
            author=report.author.value,
            created_at=report.created_at,
            version=report.version,
        )
