"""Investigation Service package.

Exposes the Investigation Service and its error types. Repository contracts live
in :mod:`app.application.investigation.repositories` and are imported directly by
the infrastructure adapters that implement them.
"""

from app.application.investigation.errors import (
    DuplicateEvidenceError,
    DuplicateInvestigationError,
    EvidenceNotFoundError,
    EvidenceOwnershipError,
    FindingNotFoundError,
    InvalidLifecycleTransitionError,
    InvestigationNotFoundError,
    InvestigationServiceError,
    InvestigationValidationError,
    ReportNotFoundError,
)
from app.application.investigation.service import InvestigationService

__all__ = [
    "InvestigationService",
    "InvestigationServiceError",
    "InvestigationNotFoundError",
    "DuplicateInvestigationError",
    "InvalidLifecycleTransitionError",
    "InvestigationValidationError",
    "EvidenceNotFoundError",
    "DuplicateEvidenceError",
    "EvidenceOwnershipError",
    "FindingNotFoundError",
    "ReportNotFoundError",
]
