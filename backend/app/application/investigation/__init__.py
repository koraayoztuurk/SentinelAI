"""Investigation Service package.

Exposes the Investigation Service and its error types. Repository contracts live
in :mod:`app.application.investigation.repositories` and are imported directly by
the infrastructure adapters that implement them.
"""

from app.application.investigation.errors import (
    DuplicateEvidenceError,
    DuplicateInvestigationError,
    DuplicateOutcomeError,
    EvidenceNotFoundError,
    EvidenceOwnershipError,
    EvidencePayloadIntegrityError,
    EvidencePayloadMissingError,
    EvidencePayloadNotFoundError,
    EvidencePayloadStoreUnavailableError,
    FindingNotFoundError,
    InvalidLifecycleTransitionError,
    InvestigationNotFoundError,
    InvestigationServiceError,
    InvestigationValidationError,
    OutcomeNotFoundError,
    ReportNotFoundError,
)
from app.application.investigation.payload_store import (
    EvidencePayloadStore,
    is_payload_address,
    payload_address,
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
    "EvidencePayloadStore",
    "EvidencePayloadStoreUnavailableError",
    "EvidencePayloadNotFoundError",
    "EvidencePayloadIntegrityError",
    "EvidencePayloadMissingError",
    "is_payload_address",
    "payload_address",
    "FindingNotFoundError",
    "ReportNotFoundError",
    "OutcomeNotFoundError",
    "DuplicateOutcomeError",
]
