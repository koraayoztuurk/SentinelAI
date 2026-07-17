"""Investigation Service exceptions.

Service-level errors raised by the Investigation Service. Each derives from the
shared :class:`~app.shared.exceptions.SentinelAIError` and carries a stable
machine-readable ``code`` so the API layer can translate them into consistent
responses without leaking internal details. Only errors tied to an enforced rule
are defined here.
"""

from app.shared.exceptions import SentinelAIError


class InvestigationServiceError(SentinelAIError):
    """Base class for Investigation Service errors."""

    code = "investigation.error"


class InvestigationNotFoundError(InvestigationServiceError):
    """Raised when a referenced investigation does not exist."""

    code = "investigation.not_found"


class DuplicateInvestigationError(InvestigationServiceError):
    """Raised when creating an investigation whose identifier already exists."""

    code = "investigation.duplicate"


class InvalidLifecycleTransitionError(InvestigationServiceError):
    """Raised when a requested lifecycle status transition is not permitted."""

    code = "investigation.invalid_transition"


class InvestigationValidationError(InvestigationServiceError):
    """Raised when an investigation fails required-field or state validation."""

    code = "investigation.invalid"


class EvidenceNotFoundError(InvestigationServiceError):
    """Raised when a referenced evidence item does not exist."""

    code = "investigation.evidence_not_found"


class DuplicateEvidenceError(InvestigationServiceError):
    """Raised when attaching an evidence item whose identifier already exists."""

    code = "investigation.duplicate_evidence"


class EvidenceOwnershipError(InvestigationServiceError):
    """Raised when an evidence item does not belong to the expected investigation."""

    code = "investigation.evidence_ownership"


class FindingNotFoundError(InvestigationServiceError):
    """Raised when a referenced finding does not exist."""

    code = "investigation.finding_not_found"


class ReportNotFoundError(InvestigationServiceError):
    """Raised when a referenced report does not exist."""

    code = "investigation.report_not_found"


class OutcomeNotFoundError(InvestigationServiceError):
    """Raised when an investigation has no synthesized outcome."""

    code = "investigation.outcome_not_found"


class DuplicateOutcomeError(InvestigationServiceError):
    """Raised when an investigation already has an outcome (0..1 per investigation)."""

    code = "investigation.duplicate_outcome"


class EvidencePayloadStoreUnavailableError(InvestigationServiceError):
    """Raised when the evidence payload store is unreachable or not composed."""

    code = "investigation.evidence_payload_store_unavailable"


class EvidencePayloadNotFoundError(InvestigationServiceError):
    """Raised when an evidence item's payload address does not resolve.

    Covers evidence without a payload (an opaque interim integrity value) and
    dangling content addresses — the reference stays observable, never
    repaired silently (database-architecture §8a).
    """

    code = "investigation.evidence_payload_not_found"


class EvidencePayloadIntegrityError(InvestigationServiceError):
    """Raised when a retrieved payload fails verification against its address.

    The content address is the verifiable integrity anchor (Domain Rule 1/9);
    a mismatch is a data-integrity fault the analyst must see, never a value
    to repair or return anyway.
    """

    code = "investigation.evidence_payload_integrity"


class EvidencePayloadMissingError(InvestigationServiceError):
    """Raised when attaching evidence whose address-shaped integrity value
    references no stored payload (a broken payload reference at creation)."""

    code = "investigation.evidence_payload_missing"
