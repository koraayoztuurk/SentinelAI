"""Seed a demonstrable SentinelAI environment (ES-053).

Creates a small, consistent demo dataset across every authoritative store —
through the **services**, never raw persistence — and projects the seeded
Memory Items into Qdrant, proving the second vertical slice end to end:

1. PostgreSQL is migrated to the Alembic head.
2. The Neo4j graph schema is bootstrapped (versioned idempotent migration,
   ES-048 — this utility is its documented second invoker).
3. One demo investigation is created with evidence, confirmed findings,
   graph entities/relationships (deterministic ``demo-*`` entity ids: re-runs
   reuse them by canonical identity) and content-rich Memory Items.
4. The outbox projector runs once: with ``GOOGLE_API_KEY`` configured it
   generates **real Gemini embeddings** into Qdrant (the end-to-end
   real-embedding path ES-050 delegated here); without a key it degrades
   cleanly — the outbox records stay pending for the app's background
   projector.

Usage (from ``backend/``, stores from the compose ``data`` profile)::

    # PowerShell
    $env:POSTGRES_HOST="127.0.0.1"; $env:NEO4J_URI="bolt://127.0.0.1:7687"
    $env:QDRANT_URL="http://127.0.0.1:6333"; $env:NEO4J_PASSWORD="<compose pw>"
    .venv\\Scripts\\python.exe scripts\\seed_demo.py

The script is additive and non-destructive: each run creates a fresh demo
investigation (UUID id) and fresh Memory Items; the ``demo-*`` graph entities
are reused by identity (Graph Service idempotent creation, ES-006/ES-048).
"""

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.application.graph import GraphService
from app.application.investigation import InvestigationService
from app.application.memory import MemoryService
from app.application.memory.projector import MemoryEmbeddingProjector
from app.application.secrets import SecretNotFoundError
from app.config.ai import get_gemini_embedding_settings
from app.domain.entity import Entity
from app.domain.enums import (
    FindingStatus,
    InvestigationStatus,
    MemoryStatus,
)
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import (
    EntityId,
    EvidenceId,
    FindingId,
    InvestigationId,
    MemoryItemId,
    RelationshipId,
)
from app.domain.investigation import Investigation
from app.domain.memory_item import MemoryItem
from app.domain.relationship import Relationship
from app.domain.value_objects import (
    ActorRef,
    Confidence,
    EntityType,
    EvidenceIntegrity,
    EvidenceSource,
    MemoryType,
    Priority,
    RelationshipType,
)
from app.infrastructure.ai.gemini_embedding import GeminiEmbeddingProvider
from app.infrastructure.ai.memory_embedding import EmbeddingMemoryAdapter
from app.infrastructure.persistence.neo4j.repositories import (
    Neo4jGraphRepository,
)
from app.infrastructure.persistence.neo4j.schema import bootstrap_graph_schema
from app.infrastructure.persistence.postgres.investigation.repositories import (
    PostgresEvidenceRepository,
    PostgresFindingRepository,
    PostgresInvestigationRepository,
    PostgresOutcomeRepository,
    PostgresReportRepository,
    PostgresTraceRepository,
)
from app.infrastructure.persistence.postgres.memory.outbox_repository import (
    PostgresOutboxRepository,
)
from app.infrastructure.persistence.postgres.memory.repositories import (
    PostgresMemoryRepository,
)
from app.infrastructure.persistence.postgres.session import session_scope
from app.infrastructure.persistence.qdrant.memory_vector_store import (
    COLLECTION_NAME,
    QdrantMemoryVectorStore,
)
from app.infrastructure.persistence.registry import (
    PersistenceRegistry,
    build_registry,
)
from app.infrastructure.secrets import EnvironmentSecretProvider

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_HOST = "demo-host-1"
_IP = "demo-ip-1"
_DOMAIN = "demo-domain-1"


def _migrate_postgres() -> None:
    config = Config(str(_BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    command.upgrade(config, "head")
    print("[1/4] PostgreSQL migrated to head")


def _investigation_service(session: object) -> InvestigationService:
    return InvestigationService(
        PostgresInvestigationRepository(session),  # type: ignore[arg-type]
        PostgresEvidenceRepository(session),  # type: ignore[arg-type]
        PostgresFindingRepository(session),  # type: ignore[arg-type]
        PostgresReportRepository(session),  # type: ignore[arg-type]
        PostgresOutcomeRepository(session),  # type: ignore[arg-type]
        PostgresTraceRepository(session),  # type: ignore[arg-type]
    )


async def _seed(registry: PersistenceRegistry) -> InvestigationId:
    now = datetime.now(UTC)
    investigation_id = InvestigationId(uuid.uuid4().hex)
    evidence_beacon = EvidenceId(uuid.uuid4().hex)
    evidence_dns = EvidenceId(uuid.uuid4().hex)

    # --- Neo4j: schema + demo neighbourhood (idempotent by entity identity).
    await bootstrap_graph_schema(registry.neo4j_driver)
    print("[2/4] Neo4j graph schema at head")

    graph = GraphService(Neo4jGraphRepository(registry.neo4j_driver))
    await graph.create_entity(
        Entity(
            id=EntityId(_HOST),
            type=EntityType("endpoint"),
            display_name="HOST-1",
            confidence=Confidence(0.95),
            source="edr",
        )
    )
    await graph.create_entity(
        Entity(
            id=EntityId(_IP),
            type=EntityType("ip"),
            display_name="203.0.113.7",
            confidence=Confidence(0.9),
            source="netflow",
        )
    )
    await graph.create_entity(
        Entity(
            id=EntityId(_DOMAIN),
            type=EntityType("domain"),
            display_name="evil-cdn.example",
            confidence=Confidence(0.8),
            source="dns",
        )
    )
    # Relationship ids are fresh per run (no natural key, ES-016), so each
    # run adds its own demo edges between the reused entities.
    await graph.create_relationship(
        Relationship(
            id=RelationshipId(uuid.uuid4().hex),
            source_entity_id=EntityId(_HOST),
            target_entity_id=EntityId(_IP),
            type=RelationshipType("communicates_with"),
            confidence=Confidence(0.9),
            supporting_evidence=(evidence_beacon,),
            created_at=now,
        )
    )
    await graph.create_relationship(
        Relationship(
            id=RelationshipId(uuid.uuid4().hex),
            source_entity_id=EntityId(_DOMAIN),
            target_entity_id=EntityId(_IP),
            type=RelationshipType("resolves_to"),
            confidence=Confidence(0.85),
            supporting_evidence=(evidence_dns,),
            created_at=now,
        )
    )

    # --- PostgreSQL: investigation family + memory (one transaction).
    async with session_scope(registry.session_factory) as session:
        investigations = _investigation_service(session)
        await investigations.create(
            Investigation(
                id=investigation_id,
                title="Demo: beaconing from HOST-1",
                status=InvestigationStatus.CREATED,
                created_at=now,
                owner=ActorRef("koray"),
                priority=Priority("high"),
            )
        )
        await investigations.attach_evidence(
            Evidence(
                id=evidence_beacon,
                investigation_id=investigation_id,
                source=EvidenceSource("edr"),
                timestamp=now,
                integrity=EvidenceIntegrity("verified"),
                content=(
                    "HOST-1 opens a TLS connection to 203.0.113.7 every 60 "
                    "seconds (beacon-like periodicity)."
                ),
            )
        )
        await investigations.attach_evidence(
            Evidence(
                id=evidence_dns,
                investigation_id=investigation_id,
                source=EvidenceSource("dns"),
                timestamp=now,
                integrity=EvidenceIntegrity("verified"),
                content=(
                    "evil-cdn.example resolved to 203.0.113.7 minutes before "
                    "the first beacon."
                ),
            )
        )
        await investigations.create_finding(
            Finding(
                id=FindingId(uuid.uuid4().hex),
                investigation_id=investigation_id,
                supporting_evidence=(evidence_beacon,),
                creator=ActorRef("koray"),
                created_at=now,
                confidence=Confidence(0.85),
                status=FindingStatus.VALIDATED,
                related_entities=(EntityId(_HOST), EntityId(_IP)),
            )
        )
        await investigations.create_finding(
            Finding(
                id=FindingId(uuid.uuid4().hex),
                investigation_id=investigation_id,
                supporting_evidence=(evidence_dns,),
                creator=ActorRef("koray"),
                created_at=now,
                confidence=Confidence(0.7),
                status=FindingStatus.ACCEPTED,
                related_entities=(EntityId(_DOMAIN),),
            )
        )

        memory = MemoryService(PostgresMemoryRepository(session))
        for type_value, status, confidence, content in (
            (
                "attack_pattern",
                MemoryStatus.VERIFIED,
                0.9,
                "C2 beacons at fixed 60s intervals over TLS; the destination "
                "IP is fronted by a disposable CDN domain.",
            ),
            (
                "analyst_note",
                MemoryStatus.CANDIDATE,
                0.6,
                "Similar beaconing was observed in the March incident; the "
                "actor rotated CDN domains weekly.",
            ),
            (
                "mitigation",
                MemoryStatus.VERIFIED,
                0.8,
                "Blocking the resolved IP alone is insufficient — sinkhole "
                "the domain and alert on fixed-interval TLS flows.",
            ),
        ):
            await memory.create(
                MemoryItem(
                    id=MemoryItemId(uuid.uuid4().hex),
                    type=MemoryType(type_value),
                    source_investigation_id=investigation_id,
                    confidence=Confidence(confidence),
                    status=status,
                    created_at=now,
                    content=content,
                )
            )
    print(
        "[3/4] Seeded investigation "
        f"{investigation_id.value} (2 evidence, 2 findings, 3 memory items, "
        "3 entities, 2 relationships)"
    )
    return investigation_id


async def _project(registry: PersistenceRegistry) -> None:
    settings = get_gemini_embedding_settings()
    try:
        embedder = EmbeddingMemoryAdapter(
            GeminiEmbeddingProvider(settings, EnvironmentSecretProvider())
        )
    except SecretNotFoundError:
        print(
            "[4/4] GOOGLE_API_KEY not configured — outbox records stay "
            "pending (the app's background projector will embed them once "
            "a key is available)."
        )
        return

    store = QdrantMemoryVectorStore(registry.qdrant_client)
    # The derived collection is never authoritative (ADR-012): if an earlier
    # run (e.g. the live test suite's small fake-embedder collection) left it
    # at a different vector size, recreate it at the configured dimension.
    # Points from earlier projections are lost with it — acceptable for a
    # demo store; bulk re-projection remains a deferred capability (ES-050).
    client = registry.qdrant_client
    if await client.collection_exists(COLLECTION_NAME):
        info = await client.get_collection(COLLECTION_NAME)
        params = info.config.params.vectors
        existing = params.size if hasattr(params, "size") else None
        if existing != settings.dimensions:
            print(
                f"    (recreating '{COLLECTION_NAME}': existing dim "
                f"{existing} != configured {settings.dimensions})"
            )
            await client.delete_collection(COLLECTION_NAME)
    await store.ensure_collection(settings.dimensions)
    async with session_scope(registry.session_factory) as session:
        processed = await MemoryEmbeddingProjector(
            PostgresOutboxRepository(session),
            PostgresMemoryRepository(session),
            embedder,
            store,
        ).project_pending()
    print(
        f"[4/4] Projected {processed} Memory Item embedding(s) into Qdrant "
        "with real Gemini embeddings"
    )


async def _main() -> None:
    registry = build_registry()
    try:
        investigation_id = await _seed(registry)
        await _project(registry)
    finally:
        await registry.close()

    print()
    print("Demo ready. Walkthrough:")
    print(
        "  1. Start the backend (uvicorn app.main:app) and the frontend "
        "(npm run dev) — or docker compose --profile data up."
    )
    print(
        "  2. Sign in with the dev credential "
        "(koray:<DEV_AUTH_TOKEN> in the header field)."
    )
    print(
        f"  3. Open /investigations/{investigation_id.value}/workspace — "
        "evidence, confirmed findings, the entity graph and the Memory "
        "region are all live."
    )
    print(
        "  4. Press 'Run investigation': the planner decides over the live "
        "stack; the Retrieval Flow (ES-051) embeds the objective, searches "
        "Qdrant and observes the seeded knowledge — inspect the RETRIEVAL "
        "entry in the AI Insights trace."
    )


if __name__ == "__main__":
    # Alembic's async env drives its own event loop, so the migration runs
    # before (not inside) this script's asyncio entry point.
    _migrate_postgres()
    asyncio.run(_main())
