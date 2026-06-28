"""Report entity.

A Report is the final, human-readable output of an investigation. It organizes
existing investigation knowledge for analysts and stakeholders and does not
introduce new knowledge (Domain Rule 6). This entity models the report's
identifying metadata; report body composition is owned by a later specification.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.identifiers import InvestigationId, ReportId
from app.domain.value_objects import ActorRef


@dataclass(slots=True)
class Report:
    """Identifying metadata of an investigation report."""

    id: ReportId
    investigation_id: InvestigationId
    author: ActorRef
    created_at: datetime
    version: int = 1
