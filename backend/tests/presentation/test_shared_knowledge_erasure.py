"""Tests for shared-knowledge erasure authorization (ES-070, RFC-005/ADR-019).

The question the RFC answered was *who* may destroy organizational knowledge.
These tests hold both halves of the answer: the capability opens the operation,
and its absence closes it — including for identities that may freely read and
write the very same shared layers, which is the distinction the whole decision
rests on.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.application.authorization import (
    ERASE_SHARED_KNOWLEDGE,
    AuthorizationError,
    AuthorizationRequest,
    OwnerScopedAuthorizer,
)
from app.application.memory import MemoryService
from app.domain.enums import MemoryStatus
from app.domain.erasure import tombstone_memory_item
from app.domain.identifiers import MemoryItemId
from app.domain.memory_item import MemoryItem
from app.main import create_app
from app.presentation.api.auth import (
    AuthenticatedIdentity,
    IdentityKind,
    get_authenticator,
)
from app.presentation.api.authorization import get_authorizer
from app.presentation.api.v1.memory.dependencies import get_memory_service
from tests.support.builders import build_memory_item

pytestmark = pytest.mark.operational


class _MemoryRepo:
    def __init__(self) -> None:
        self.items: dict[str, list[MemoryItem]] = {}

    async def add(self, item: MemoryItem) -> None:
        self.items.setdefault(item.id.value, []).append(item)

    async def get(self, memory_id: MemoryItemId) -> MemoryItem | None:
        versions = self.items.get(memory_id.value)
        return versions[-1] if versions else None

    async def update(self, item: MemoryItem) -> None:
        self.items[item.id.value][-1] = item

    async def list_versions(
        self, memory_id: MemoryItemId
    ) -> tuple[MemoryItem, ...]:
        return tuple(self.items.get(memory_id.value, ()))

    async def list_for_investigation(
        self, investigation_id: object
    ) -> tuple[MemoryItem, ...]:
        return ()

    async def erase(self, memory_id: MemoryItemId) -> None:
        versions = self.items.get(memory_id.value, [])
        self.items[memory_id.value] = [
            tombstone_memory_item(item) for item in versions
        ]


def _identity(*capabilities: str) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        subject="analyst",
        kind=IdentityKind.HUMAN,
        capabilities=frozenset(capabilities),
    )


def _client(identity: AuthenticatedIdentity) -> tuple[TestClient, _MemoryRepo]:
    repo = _MemoryRepo()
    asyncio.run(repo.add(build_memory_item("mem-1")))
    app = create_app()

    class _Authenticator:
        async def authenticate(self, request: object) -> AuthenticatedIdentity:
            return identity

    app.dependency_overrides[get_authenticator] = _Authenticator
    # The real policy, not a stub: the capability gate is the thing under
    # test, so a permissive double would test nothing. A shared-knowledge
    # operation names no investigation, so the policy never consults the
    # Investigation Service.
    app.dependency_overrides[get_authorizer] = lambda: OwnerScopedAuthorizer(
        None  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_memory_service] = lambda: MemoryService(repo)
    return TestClient(app), repo


# ------------------------------------------------------------------- policy


def _authorize(operation: str, *capabilities: str) -> None:
    authorizer = OwnerScopedAuthorizer(None)  # type: ignore[arg-type]
    asyncio.run(
        authorizer.authorize(
            AuthorizationRequest(
                subject="analyst",
                identity_kind="human",
                operation=operation,
                capabilities=frozenset(capabilities),
            )
        )
    )


def test_reading_shared_knowledge_needs_no_capability() -> None:
    # §6a is untouched: the promotion boundary still makes retrieval open.
    _authorize("GET /api/v1/memory")
    _authorize("GET /api/v1/graph/entities/e-1")


def test_writing_shared_knowledge_needs_no_capability() -> None:
    _authorize("POST /api/v1/memory")
    _authorize("POST /api/v1/graph/entities")


def test_erasing_shared_knowledge_requires_the_capability() -> None:
    with pytest.raises(AuthorizationError):
        _authorize("DELETE /api/v1/memory/mem-1")
    with pytest.raises(AuthorizationError):
        _authorize("DELETE /api/v1/graph/entities/e-1")


def test_the_capability_permits_the_erasure() -> None:
    _authorize("DELETE /api/v1/memory/mem-1", ERASE_SHARED_KNOWLEDGE)
    _authorize("DELETE /api/v1/graph/entities/e-1", ERASE_SHARED_KNOWLEDGE)


def test_an_unrelated_capability_does_not_open_the_operation() -> None:
    with pytest.raises(AuthorizationError):
        _authorize("DELETE /api/v1/memory/mem-1", "something:else")


# --------------------------------------------------------------------- API


def test_erasure_is_denied_without_the_capability() -> None:
    client, repo = _client(_identity())

    response = client.delete("/api/v1/memory/mem-1")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "authorization.denied"
    # The knowledge is untouched — a denied destructive request must change
    # nothing at all.
    assert repo.items["mem-1"][-1].status is not MemoryStatus.ERASED


def test_erasure_succeeds_with_the_capability() -> None:
    client, repo = _client(_identity(ERASE_SHARED_KNOWLEDGE))

    response = client.delete("/api/v1/memory/mem-1")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "erased"
    assert repo.items["mem-1"][-1].status is MemoryStatus.ERASED


def test_erasure_is_idempotent() -> None:
    client, _ = _client(_identity(ERASE_SHARED_KNOWLEDGE))

    client.delete("/api/v1/memory/mem-1")
    second = client.delete("/api/v1/memory/mem-1")

    assert second.status_code == 200
    assert second.json()["data"]["status"] == "erased"
