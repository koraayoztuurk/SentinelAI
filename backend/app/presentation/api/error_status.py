"""Error-to-HTTP-status translation.

Maps application/domain error codes to HTTP status codes at the presentation
boundary (api-design §11: error translation is an API responsibility). The mapping
is an explicit, stable table keyed by each error's ``code`` constant — HTTP concerns
never leak into the application or domain layers. Unknown codes fall back to 400.
"""

from app.application.authorization.errors import AuthorizationError
from app.application.graph.errors import (
    EntityNotFoundError,
    GraphStoreUnavailableError,
    RelationshipNotFoundError,
)
from app.application.investigation.errors import (
    DuplicateEvidenceError,
    DuplicateInvestigationError,
    EvidenceNotFoundError,
    EvidenceOwnershipError,
    EvidencePayloadIntegrityError,
    EvidencePayloadMissingError,
    EvidencePayloadNotFoundError,
    EvidencePayloadStoreUnavailableError,
    FindingNotFoundError,
    InvalidLifecycleTransitionError,
    InvestigationNotFoundError,
    InvestigationValidationError,
    OutcomeNotFoundError,
    ReportNotFoundError,
)
from app.application.memory.errors import (
    DuplicateMemoryError,
    InvalidMemoryVersionError,
    MemoryNotFoundError,
)
from app.application.planner.errors import InvalidActionError
from app.application.secrets import SecretNotFoundError
from app.domain.exceptions import (
    BlankValueError,
    InvalidConfidenceError,
    MissingSupportingEvidenceError,
)
from app.presentation.api.errors import (
    AuthenticationError,
    InvalidPayloadError,
    PayloadTooLargeError,
    PersistenceUnavailableError,
    ServiceNotConfiguredError,
)
from app.shared.exceptions import SentinelAIError

_DEFAULT_STATUS = 400

_STATUS_BY_CODE: dict[str, int] = {
    InvestigationNotFoundError.code: 404,
    EvidenceNotFoundError.code: 404,
    FindingNotFoundError.code: 404,
    ReportNotFoundError.code: 404,
    OutcomeNotFoundError.code: 404,
    DuplicateInvestigationError.code: 409,
    DuplicateEvidenceError.code: 409,
    InvalidLifecycleTransitionError.code: 409,
    InvestigationValidationError.code: 422,
    EvidenceOwnershipError.code: 422,
    # Evidence payload family (ES-060, ADR-015): a missing payload is 404, a
    # broken attach-time reference is a validation failure, a verification
    # mismatch is a data-integrity conflict, an unreachable/unconfigured
    # store an operational condition.
    EvidencePayloadNotFoundError.code: 404,
    EvidencePayloadMissingError.code: 422,
    EvidencePayloadIntegrityError.code: 409,
    EvidencePayloadStoreUnavailableError.code: 503,
    PayloadTooLargeError.code: 413,
    InvalidPayloadError.code: 422,
    EntityNotFoundError.code: 404,
    RelationshipNotFoundError.code: 404,
    MemoryNotFoundError.code: 404,
    DuplicateMemoryError.code: 409,
    InvalidMemoryVersionError.code: 422,
    InvalidActionError.code: 422,
    AuthenticationError.code: 401,
    AuthorizationError.code: 403,
    BlankValueError.code: 422,
    InvalidConfidenceError.code: 422,
    MissingSupportingEvidenceError.code: 422,
    ServiceNotConfiguredError.code: 503,
    PersistenceUnavailableError.code: 503,
    GraphStoreUnavailableError.code: 503,
    # A missing provider secret is a server-side configuration condition
    # (e.g. the run surface without GOOGLE_API_KEY), not a client error.
    SecretNotFoundError.code: 503,
}


def http_status_for(error: SentinelAIError) -> int:
    """Return the HTTP status code for an application/domain error."""

    return _STATUS_BY_CODE.get(error.code, _DEFAULT_STATUS)
