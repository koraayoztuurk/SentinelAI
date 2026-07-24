"""Unit tests for investigation erasure (ES-064, ADR-017).

Plain pytest functions over the shared in-memory doubles. Erasure tombstones an
investigation and its scoped objects (personal content redacted, identifiers /
timestamps / owner+tenant preserved), is idempotent, rejects business writes to
an erased investigation, and blocks payload access — all without a database.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.application.investigation import (
    EvidencePayloadNotFoundError,
    InvestigationErasedError,
    InvestigationNotFoundError,
    InvestigationService,
    payload_address,
)
from app.domain.enums import InvestigationOutcomeStatus, InvestigationStatus
from app.domain.erasure import REDACTED
from app.domain.identifiers import (
    EvidenceId,
    InvestigationId,
    InvestigationOutcomeId,
    TraceEntryId,
)
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import ActorRef, Confidence
from tests.support.builders import (
    build_evidence,
    build_investigation,
)
from tests.support.doubles import (
    InMemoryEvidencePayloadStore,
    InMemoryEvidenceRepository,
    InMemoryFindingRepository,
    InMemoryInvestigationRepository,
    InMemoryOutcomeRepository,
    InMemoryReportRepository,
    InMemoryTraceRepository,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_ERASED_AT = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)


def _service(
    *,
    payloads: InMemoryEvidencePayloadStore | None = None,
) -> tuple[
    InvestigationService,
    InMemoryInvestigationRepository,
    InMemoryEvidenceRepository,
    InMemoryOutcomeRepository,
    InMemoryTraceRepository,
]:
    investigations = InMemoryInvestigationRepository()
    evidence = InMemoryEvidenceRepository()
    outcomes = InMemoryOutcomeRepository()
    trace = InMemoryTraceRepository()
    service = InvestigationService(
        investigations,
        evidence,
        InMemoryFindingRepository(),
        InMemoryReportRepository(),
        outcomes,
        trace,
        payloads=payloads,
    )
    return service, investigations, evidence, outcomes, trace


async def _seed_active(
    investigations: InMemoryInvestigationRepository,
    investigation_id: str = "inv-1",
    *,
    owner: str = "analyst-1",
    tenant: str = "acme",
) -> None:
    await investigations.add(
        build_investigation(
            investigation_id,
            status=InvestigationStatus.ACTIVE,
            owner=owner,
            tenant=tenant,
            created_at=_NOW,
        )
    )


def _outcome(investigation_id: str) -> InvestigationOutcome:
    return InvestigationOutcome(
        id=InvestigationOutcomeId("oc-1"),
        investigation_id=InvestigationId(investigation_id),
        confidence=Confidence(0.7),
        recommendation="escalate to tier 2 for user jane.doe",
        status=InvestigationOutcomeStatus.SYNTHESIZED,
        created_at=_NOW,
        contributing_findings=(),
        detected_conflicts=("conflict about jane.doe",),
        open_questions=("who is jane.doe",),
    )


def _trace_entry(investigation_id: str) -> TraceEntry:
    return TraceEntry(
        id=TraceEntryId("tr-1"),
        investigation_id=InvestigationId(investigation_id),
        kind=TraceEntryKind.ANALYST_NOTE,
        actor=ActorRef("analyst-1"),
        summary="sensitive reasoning naming jane.doe",
        reference="ref-1",
        created_at=_NOW,
    )


def test_erase_tombstones_the_investigation() -> None:
    async def scenario() -> None:
        service, investigations, *_ = _service()
        await _seed_active(investigations, owner="analyst-1", tenant="acme")

        tombstone = await service.erase(InvestigationId("inv-1"), _ERASED_AT)

        assert tombstone.status is InvestigationStatus.ERASED
        assert tombstone.title == REDACTED
        assert tombstone.erased_at == _ERASED_AT
        # Correlation structure survives so authorization still resolves.
        assert tombstone.owner == ActorRef("analyst-1")
        assert tombstone.tenant.value == "acme"
        assert tombstone.created_at == _NOW

    asyncio.run(scenario())


def test_erase_cascades_and_redacts_scoped_personal_content() -> None:
    async def scenario() -> None:
        service, investigations, evidence, outcomes, trace = _service()
        await _seed_active(investigations)
        await service.attach_evidence(
            build_evidence(
                "ev-1",
                "inv-1",
                source="dns-logs",
                integrity="sha256:" + "a" * 64,
                content="raw personal payload for jane.doe",
            )
        )
        await service.create_outcome(_outcome("inv-1"))
        await service.record_trace(_trace_entry("inv-1"))

        await service.erase(InvestigationId("inv-1"), _ERASED_AT)

        (erased_evidence,) = await evidence.list_for_investigation(
            InvestigationId("inv-1")
        )
        assert erased_evidence.content == REDACTED
        assert erased_evidence.source.value == REDACTED
        # The content address (a hash) is retained so ES-065 can shred bytes.
        assert erased_evidence.integrity.value == "sha256:" + "a" * 64
        assert erased_evidence.id.value == "ev-1"

        erased_outcome = await outcomes.get_for_investigation(
            InvestigationId("inv-1")
        )
        assert erased_outcome is not None
        assert erased_outcome.recommendation == REDACTED
        assert erased_outcome.detected_conflicts == ()
        assert erased_outcome.open_questions == ()
        assert erased_outcome.status is InvestigationOutcomeStatus.SYNTHESIZED

        (erased_entry,) = await trace.list_for_investigation(
            InvestigationId("inv-1")
        )
        assert erased_entry.summary == REDACTED
        assert erased_entry.kind is TraceEntryKind.ANALYST_NOTE
        assert erased_entry.reference == "ref-1"

    asyncio.run(scenario())


def test_erase_is_idempotent() -> None:
    async def scenario() -> None:
        service, investigations, *_ = _service()
        await _seed_active(investigations)

        first = await service.erase(InvestigationId("inv-1"), _ERASED_AT)
        second = await service.erase(
            InvestigationId("inv-1"), datetime(2027, 1, 1, tzinfo=UTC)
        )

        # Re-erasure is a no-op returning the existing tombstone: the erasure
        # timestamp does not move.
        assert second.erased_at == first.erased_at == _ERASED_AT
        assert second.status is InvestigationStatus.ERASED

    asyncio.run(scenario())


def test_erase_unknown_investigation_raises_not_found() -> None:
    async def scenario() -> None:
        service, *_ = _service()
        with pytest.raises(InvestigationNotFoundError):
            await service.erase(InvestigationId("missing"), _ERASED_AT)

    asyncio.run(scenario())


def test_reads_resolve_to_the_tombstone_never_disappear() -> None:
    async def scenario() -> None:
        service, investigations, *_ = _service()
        await _seed_active(investigations)
        await service.attach_evidence(build_evidence("ev-1", "inv-1"))

        await service.erase(InvestigationId("inv-1"), _ERASED_AT)

        fetched = await service.get(InvestigationId("inv-1"))
        assert fetched.status is InvestigationStatus.ERASED
        listed = await service.list_evidence(InvestigationId("inv-1"))
        assert [e.id.value for e in listed] == ["ev-1"]

    asyncio.run(scenario())


def test_business_writes_to_an_erased_investigation_are_rejected() -> None:
    async def scenario() -> None:
        service, investigations, *_ = _service()
        await _seed_active(investigations)
        await service.erase(InvestigationId("inv-1"), _ERASED_AT)

        with pytest.raises(InvestigationErasedError):
            await service.attach_evidence(build_evidence("ev-2", "inv-1"))
        with pytest.raises(InvestigationErasedError):
            await service.record_trace(_trace_entry("inv-1"))
        with pytest.raises(InvestigationErasedError):
            await service.create_outcome(_outcome("inv-1"))
        with pytest.raises(InvestigationErasedError):
            await service.change_status(
                InvestigationId("inv-1"), InvestigationStatus.ACTIVE
            )

    asyncio.run(scenario())


def test_payload_access_is_blocked_after_erasure() -> None:
    async def scenario() -> None:
        payloads = InMemoryEvidencePayloadStore()
        service, investigations, *_ = _service(payloads=payloads)
        await _seed_active(investigations)
        content = b"raw payload bytes"
        address = payload_address(content)
        await payloads.put(address, content)
        await service.attach_evidence(
            build_evidence("ev-1", "inv-1", integrity=address)
        )

        # Live: the payload downloads and verifies.
        assert (
            await service.get_evidence_payload(EvidenceId("ev-1")) == content
        )

        await service.erase(InvestigationId("inv-1"), _ERASED_AT)

        # Erased: the payload resolves to "not available" (§8a), never the bytes.
        with pytest.raises(EvidencePayloadNotFoundError):
            await service.get_evidence_payload(EvidenceId("ev-1"))

    asyncio.run(scenario())
