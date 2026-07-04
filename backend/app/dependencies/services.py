"""Live backend-service providers (runtime persistence binding, ES-042).

Composition root for the request-scoped service graph: builds the
Investigation, Memory and Planner services over the concrete PostgreSQL
adapters (ES-040/041) and binds them to the presentation dependency seams via
``FastAPI.dependency_overrides`` in :func:`bind_live_services`. This package
may see every layer; the presentation dependencies themselves keep their
explicit unbound default (503) and never import infrastructure (AC-05).

Transaction model: one request = one session = one local transaction. Every
provider opens a request-scoped session from the persistence registry
(``session_scope`` commits on success, rolls back on error); the whole
adapter set of the request shares it. The Planner composition uses the
explicit-contract unavailable graph repository — the graph store is outside
the first vertical slice, so graph actions produce a contained failed result
with the stable ``graph.store_unavailable`` code (the Graph API itself stays
unbound).

Failure contract: without a persistence registry (startup has not run) a
provider reports :class:`ServiceNotConfiguredError` (503, unchanged code);
with a registry but an unreachable PostgreSQL, the connectivity failure is
translated to :class:`PersistenceUnavailableError`
(503, ``api.persistence_unavailable``) — an operational condition with a
stable code, never a leaked driver exception. Data-level database errors
(e.g. constraint violations) are not masked.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.planner.agent import PlannerAgent
from app.ai.orchestration.assembler import InvestigationStateAssembler
from app.ai.orchestration.loop import InvestigationLoop
from app.ai.orchestration.runner import InvestigationRunner
from app.application.authorization import (
    Authorizer,
    DenyAllAuthorizer,
    OwnerScopedAuthorizer,
)
from app.application.graph import GraphService
from app.application.investigation import InvestigationService
from app.application.memory import MemoryService
from app.application.planner import PlannerService
from app.config.ai import get_gemini_settings
from app.config.settings import get_settings
from app.infrastructure.ai.gemini import GeminiLLMProvider
from app.infrastructure.persistence.neo4j.unavailable import (
    UnavailableGraphRepository,
)
from app.infrastructure.persistence.postgres.investigation.repositories import (
    PostgresEvidenceRepository,
    PostgresFindingRepository,
    PostgresInvestigationRepository,
    PostgresOutcomeRepository,
    PostgresReportRepository,
    PostgresTraceRepository,
)
from app.infrastructure.persistence.postgres.memory.repositories import (
    PostgresMemoryRepository,
)
from app.infrastructure.persistence.postgres.session import session_scope
from app.infrastructure.persistence.registry import PersistenceRegistry
from app.infrastructure.secrets import EnvironmentSecretProvider
from app.presentation.api.auth import (
    Authenticator,
    SharedTokenAuthenticator,
    get_authenticator,
)
from app.presentation.api.authorization import get_authorizer
from app.presentation.api.errors import (
    PersistenceUnavailableError,
    ServiceNotConfiguredError,
)
from app.presentation.api.generation import SystemClock, Uuid4IdGenerator
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_runner,
    get_investigation_service,
)
from app.presentation.api.v1.memory.dependencies import get_memory_service


def _registry(request: Request) -> PersistenceRegistry:
    registry = getattr(request.app.state, "persistence", None)
    if not isinstance(registry, PersistenceRegistry):
        raise ServiceNotConfiguredError(
            "The persistence registry is not initialized "
            "(application startup has not run)."
        )
    return registry


@asynccontextmanager
async def _request_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield the request-scoped transactional session.

    Connectivity failures — from opening the connection or surfacing later
    through the transaction — are translated to the stable
    ``api.persistence_unavailable`` contract.
    """

    try:
        async with session_scope(_registry(request).session_factory) as session:
            yield session
    except (OperationalError, InterfaceError, OSError) as exc:
        raise PersistenceUnavailableError(
            "The persistence store is unreachable."
        ) from exc


def _investigation_service(session: AsyncSession) -> InvestigationService:
    return InvestigationService(
        PostgresInvestigationRepository(session),
        PostgresEvidenceRepository(session),
        PostgresFindingRepository(session),
        PostgresReportRepository(session),
        PostgresOutcomeRepository(session),
        PostgresTraceRepository(session),
    )


async def live_investigation_service(
    request: Request,
) -> AsyncIterator[InvestigationService]:
    """Provide the Investigation Service over the live PostgreSQL adapters."""

    async with _request_session(request) as session:
        yield _investigation_service(session)


async def live_memory_service(request: Request) -> AsyncIterator[MemoryService]:
    """Provide the Memory Service over the live PostgreSQL adapter."""

    async with _request_session(request) as session:
        yield MemoryService(PostgresMemoryRepository(session))


def _planner_service(session: AsyncSession) -> PlannerService:
    """The Planner Service over the live composition (loop executor, ES-044).

    Investigation and Memory share the request's session/transaction; the
    graph dependency is the explicit-contract unavailable store, so graph
    actions produce contained failed results with a stable code.
    """

    return PlannerService(
        _investigation_service(session),
        GraphService(UnavailableGraphRepository()),
        MemoryService(PostgresMemoryRepository(session)),
    )


async def live_investigation_runner(
    request: Request,
) -> AsyncIterator[InvestigationRunner]:
    """Provide the Investigation Loop run composition (ES-044).

    Composes the Planner Agent over the Gemini provider (ES-043; the key is
    resolved through the SecretProvider — missing key is an explicit 503
    configuration error), the live Planner Service as executor, the concrete
    State Assembler and the Investigation Service as trace sink — all over
    the request's single transactional session. Identifiers/timestamps come
    from the API boundary's uuid/clock sources (the composition itself
    generates none).
    """

    async with _request_session(request) as session:
        investigation = _investigation_service(session)
        agent = PlannerAgent(
            GeminiLLMProvider(get_gemini_settings(), EnvironmentSecretProvider())
        )
        assembler = InvestigationStateAssembler(investigation)
        loop = InvestigationLoop(
            agent,
            _planner_service(session),
            assembler,
            Uuid4IdGenerator(),
            SystemClock(),
            investigation,
            get_settings().run_cycle_budget,
        )
        yield InvestigationRunner(assembler, loop)


def live_authenticator() -> Authenticator:
    """Provide the development-grade shared-token authenticator (ES-046).

    The shared secret (``DEV_AUTH_TOKEN``) is resolved through the
    SecretProvider at authenticate time; without it every request stays 401
    (secure by default, identical to the unconfigured seam).
    """

    return SharedTokenAuthenticator(EnvironmentSecretProvider())


async def live_authorizer(request: Request) -> AsyncIterator[Authorizer]:
    """Provide the owner-scoped authorization policy (ES-046, §6a).

    The policy consults the live Investigation Service for ownership over its
    own request-scoped read session. Without a persistence registry (startup
    never ran) it falls back to the default-deny authorizer, so lifespan-less
    setups keep the exact pre-policy behavior (403).
    """

    registry = getattr(request.app.state, "persistence", None)
    if not isinstance(registry, PersistenceRegistry):
        yield DenyAllAuthorizer()
        return
    async with _request_session(request) as session:
        yield OwnerScopedAuthorizer(_investigation_service(session))


def bind_live_services(app: FastAPI) -> None:
    """Bind the live providers to the presentation dependency seams.

    ``dependency_overrides`` is FastAPI's runtime substitution point; tests
    that install their own overrides after ``create_app`` still win. The
    Graph Service seam is deliberately not bound (graph store out of slice —
    its endpoints keep reporting 503).
    """

    app.dependency_overrides[get_investigation_service] = (
        live_investigation_service
    )
    app.dependency_overrides[get_memory_service] = live_memory_service
    app.dependency_overrides[get_investigation_runner] = (
        live_investigation_runner
    )
    app.dependency_overrides[get_authenticator] = live_authenticator
    app.dependency_overrides[get_authorizer] = live_authorizer
