"""Error-to-HTTP-status translation.

Maps application/domain error codes to HTTP status codes at the presentation
boundary (api-design §11: error translation is an API responsibility). The mapping
is an explicit, stable table keyed by each error's ``code`` constant — HTTP concerns
never leak into the application or domain layers. Unknown codes fall back to 400.
"""

from app.application.graph.errors import (
    EntityNotFoundError,
    RelationshipNotFoundError,
)
from app.application.investigation.errors import (
    DuplicateEvidenceError,
    DuplicateInvestigationError,
    EvidenceNotFoundError,
    EvidenceOwnershipError,
    FindingNotFoundError,
    InvalidLifecycleTransitionError,
    InvestigationNotFoundError,
    InvestigationValidationError,
    ReportNotFoundError,
)
from app.application.memory.errors import (
    DuplicateMemoryError,
    InvalidMemoryVersionError,
    MemoryNotFoundError,
)
from app.domain.exceptions import (
    BlankValueError,
    InvalidConfidenceError,
    MissingSupportingEvidenceError,
)
from app.presentation.api.errors import ServiceNotConfiguredError
from app.shared.exceptions import SentinelAIError

_DEFAULT_STATUS = 400

_STATUS_BY_CODE: dict[str, int] = {
    InvestigationNotFoundError.code: 404,
    EvidenceNotFoundError.code: 404,
    FindingNotFoundError.code: 404,
    ReportNotFoundError.code: 404,
    DuplicateInvestigationError.code: 409,
    DuplicateEvidenceError.code: 409,
    InvalidLifecycleTransitionError.code: 409,
    InvestigationValidationError.code: 422,
    EvidenceOwnershipError.code: 422,
    EntityNotFoundError.code: 404,
    RelationshipNotFoundError.code: 404,
    MemoryNotFoundError.code: 404,
    DuplicateMemoryError.code: 409,
    InvalidMemoryVersionError.code: 422,
    BlankValueError.code: 422,
    InvalidConfidenceError.code: 422,
    MissingSupportingEvidenceError.code: 422,
    ServiceNotConfiguredError.code: 503,
}


def http_status_for(error: SentinelAIError) -> int:
    """Return the HTTP status code for an application/domain error."""

    return _STATUS_BY_CODE.get(error.code, _DEFAULT_STATUS)
