"""Tests for the owner-scoped authorization policy (ES-046).

Direct decision-level validation of ``OwnerScopedAuthorizer`` (§6a): the
owner passes, a foreign subject is denied with the stable code, unknown
investigations defer to the owning service, creation and the shared
knowledge layers stay open to authenticated identities, and unrecognized
operations are denied (least privilege). In-memory doubles, plain functions.
"""

import asyncio

import pytest

from app.application.authorization import (
    AuthorizationError,
    AuthorizationRequest,
    OperationContext,
    OwnerScopedAuthorizer,
)
from tests.support.builders import build_investigation, make_investigation_service

_CONTEXT = OperationContext(
    subject="alice", identity_kind="human", correlation_id="corr-1"
)


def _request(
    operation: str,
    *,
    subject: str = "alice",
    tenant: str = "default",
    investigation_id: str | None = None,
) -> AuthorizationRequest:
    return AuthorizationRequest(
        subject=subject,
        identity_kind="human",
        operation=operation,
        correlation_id="corr-1",
        investigation_id=investigation_id,
        tenant=tenant,
    )


def _authorizer_with_investigation(
    *, owner: str = "alice", tenant: str = "default"
) -> OwnerScopedAuthorizer:
    service = make_investigation_service()
    asyncio.run(
        service.create(
            build_investigation("inv-1", owner=owner, tenant=tenant)
        )
    )
    return OwnerScopedAuthorizer(service)


def test_owner_is_permitted_on_investigation_scoped_operations() -> None:
    authorizer = _authorizer_with_investigation()
    asyncio.run(
        authorizer.authorize(
            _request(
                "GET /api/v1/investigations/inv-1",
                subject="alice",
                investigation_id="inv-1",
            )
        )
    )


def test_foreign_subject_is_denied_with_stable_code() -> None:
    authorizer = _authorizer_with_investigation()
    with pytest.raises(AuthorizationError) as excinfo:
        asyncio.run(
            authorizer.authorize(
                _request(
                    "GET /api/v1/investigations/inv-1",
                    subject="mallory",
                    investigation_id="inv-1",
                )
            )
        )
    assert excinfo.value.code == "authorization.denied"


def test_foreign_tenant_is_denied_even_for_the_owner() -> None:
    # Tenant isolation (ADR-016): the owner in another tenant cannot reach the
    # investigation — cross-tenant access is denied before the owner rule.
    authorizer = _authorizer_with_investigation(owner="alice", tenant="acme")
    with pytest.raises(AuthorizationError) as excinfo:
        asyncio.run(
            authorizer.authorize(
                _request(
                    "GET /api/v1/investigations/inv-1",
                    subject="alice",
                    tenant="default",
                    investigation_id="inv-1",
                )
            )
        )
    assert excinfo.value.code == "authorization.denied"


def test_matching_tenant_and_owner_is_permitted() -> None:
    authorizer = _authorizer_with_investigation(owner="alice", tenant="acme")
    asyncio.run(
        authorizer.authorize(
            _request(
                "GET /api/v1/investigations/inv-1",
                subject="alice",
                tenant="acme",
                investigation_id="inv-1",
            )
        )
    )


def test_unknown_investigation_defers_to_the_owning_service() -> None:
    authorizer = OwnerScopedAuthorizer(make_investigation_service())
    # Permitted: the resource owner reports the documented 404.
    asyncio.run(
        authorizer.authorize(
            _request(
                "GET /api/v1/investigations/missing",
                investigation_id="missing",
            )
        )
    )


def test_creating_investigations_is_open_to_authenticated_identities() -> None:
    authorizer = OwnerScopedAuthorizer(make_investigation_service())
    asyncio.run(authorizer.authorize(_request("POST /api/v1/investigations")))


def test_shared_knowledge_layers_are_cross_investigation() -> None:
    authorizer = OwnerScopedAuthorizer(make_investigation_service())
    asyncio.run(authorizer.authorize(_request("POST /api/v1/memory")))
    asyncio.run(
        authorizer.authorize(_request("GET /api/v1/graph/entities/e-1"))
    )


def test_unrecognized_operations_are_denied() -> None:
    authorizer = OwnerScopedAuthorizer(make_investigation_service())
    with pytest.raises(AuthorizationError):
        asyncio.run(authorizer.authorize(_request("GET /api/v1/somethingelse")))


def test_for_context_carries_the_operation_context() -> None:
    request = AuthorizationRequest.for_context(
        _CONTEXT,
        operation="GET /api/v1/investigations/inv-1",
        investigation_id="inv-1",
    )
    assert request.subject == "alice"
    assert request.identity_kind == "human"
    assert request.correlation_id == "corr-1"
    assert request.investigation_id == "inv-1"
    assert request.tenant == "default"


def test_for_context_carries_the_tenant_scope() -> None:
    context = OperationContext(
        subject="alice",
        identity_kind="human",
        correlation_id="corr-1",
        tenant="acme",
    )
    request = AuthorizationRequest.for_context(
        context, operation="GET /api/v1/investigations/inv-1"
    )
    assert request.tenant == "acme"
