"""Owner-scoped authorization policy (ES-046).

First concrete :class:`~app.application.authorization.Authorizer` policy,
realizing the Investigation Access Scoping Model (authentication-authorization
§6a): ownership is the access-scoping key for the investigation and every
investigation-scoped object (evidence, findings, reports, outcome, trace,
run); the shared knowledge layers (organizational Memory, the Knowledge
Graph) are deliberately cross-investigation, so authenticated access to them
is legitimate (§6a Shared Knowledge Boundary — isolation happens at
promotion, not retrieval).

Decision rules over the boundary-supplied ``AuthorizationRequest``:

- an operation naming an ``investigation_id`` is permitted only when the
  identity's tenant matches the investigation's tenant (cross-tenant → 403,
  ADR-016) **and** the identity is the investigation's owner (foreign owner →
  403); tenant isolation is an added conjunct over owner scoping, never a
  relaxation;
- an operation on an investigation that does not exist is permitted — the
  owning service reports the documented 404 (existence handling stays with
  the resource owner);
- creating investigations and using the shared knowledge surfaces
  (``/api/v1/memory``, ``/api/v1/graph``) is permitted for any authenticated
  identity;
- anything else is denied (least privilege: a future surface stays closed
  until this policy learns it).

The policy consults the Investigation Service interface for the investigation's
scope — never another service's persistence contracts (AC-07).
"""

from app.application.authorization.authorizer import AuthorizationRequest
from app.application.authorization.errors import AuthorizationError
from app.application.investigation import (
    InvestigationNotFoundError,
    InvestigationService,
)
from app.domain.identifiers import InvestigationId

_CREATE_INVESTIGATION_PATH = "/api/v1/investigations"
_SHARED_KNOWLEDGE_PREFIXES = ("/api/v1/memory", "/api/v1/graph")


class OwnerScopedAuthorizer:
    """Owner-based investigation scoping policy (§6a)."""

    def __init__(self, investigations: InvestigationService) -> None:
        self._investigations = investigations

    async def authorize(self, request: AuthorizationRequest) -> None:
        if request.investigation_id is not None:
            await self._authorize_investigation_scoped(
                request.investigation_id, request.subject, request.tenant
            )
            return

        path = self._path_of(request.operation)
        if path == _CREATE_INVESTIGATION_PATH:
            return
        if path.startswith(_SHARED_KNOWLEDGE_PREFIXES):
            return
        raise AuthorizationError("Operation not permitted.")

    async def _authorize_investigation_scoped(
        self, investigation_id: str, subject: str, tenant: str
    ) -> None:
        try:
            investigation = await self._investigations.get(
                InvestigationId(investigation_id)
            )
        except InvestigationNotFoundError:
            # Existence handling belongs to the owning service (404 there).
            return
        # Tenant isolation first (ADR-016): another organization's
        # investigation is invisible regardless of owner. Then the owner rule.
        if investigation.tenant.value != tenant:
            raise AuthorizationError("Investigation access denied.")
        if investigation.owner.value != subject:
            raise AuthorizationError("Investigation access denied.")

    @staticmethod
    def _path_of(operation: str) -> str:
        # The boundary's operation identifier is "<METHOD> <path>" (ES-020).
        _, _, path = operation.partition(" ")
        return path or operation
