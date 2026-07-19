"""Investigation entity.

The Investigation is the primary operational object of SentinelAI: an isolated
workspace coordinating the lifecycle of incident analysis. It owns investigation
business state. Its evidence, findings, tasks and reports are independent objects
that reference the investigation by identifier rather than being embedded here,
preserving the service-ownership boundaries defined in ADR-004.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import InvestigationStatus
from app.domain.identifiers import InvestigationId, TenantId
from app.domain.value_objects import ActorRef, Priority


@dataclass(slots=True)
class Investigation:
    """An investigation workspace and its business state."""

    id: InvestigationId
    title: str
    status: InvestigationStatus
    created_at: datetime
    owner: ActorRef
    priority: Priority
    # Organization/team access scope (ADR-016, §6a): the isolation boundary
    # the authorization policy evaluates, layered over owner scoping. Supplied
    # from the authenticated identity's tenant at creation.
    tenant: TenantId
