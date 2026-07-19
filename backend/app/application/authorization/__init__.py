"""Authorization package.

Exposes the Application Domain's authorization decision contract: the
``Authorizer`` port, the ``AuthorizationRequest`` it evaluates, the ``§6b``
``OperationContext`` it is built from, the default-deny ``DenyAllAuthorizer``,
the concrete ``OwnerScopedAuthorizer`` policy (ES-046) and the
``AuthorizationError`` raised on denial.
"""

from app.application.authorization.authorizer import (
    DEFAULT_TENANT,
    AuthorizationRequest,
    Authorizer,
    DenyAllAuthorizer,
    OperationContext,
)
from app.application.authorization.errors import AuthorizationError
from app.application.authorization.policy import OwnerScopedAuthorizer

__all__ = [
    "Authorizer",
    "AuthorizationRequest",
    "OperationContext",
    "DEFAULT_TENANT",
    "DenyAllAuthorizer",
    "OwnerScopedAuthorizer",
    "AuthorizationError",
]
