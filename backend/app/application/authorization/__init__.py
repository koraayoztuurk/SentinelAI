"""Authorization package.

Exposes the Application Domain's authorization decision contract: the
``Authorizer`` port, the ``AuthorizationRequest`` it evaluates, the default-deny
``DenyAllAuthorizer`` and the ``AuthorizationError`` raised on denial.
"""

from app.application.authorization.authorizer import (
    AuthorizationRequest,
    Authorizer,
    DenyAllAuthorizer,
)
from app.application.authorization.errors import AuthorizationError

__all__ = [
    "Authorizer",
    "AuthorizationRequest",
    "DenyAllAuthorizer",
    "AuthorizationError",
]
