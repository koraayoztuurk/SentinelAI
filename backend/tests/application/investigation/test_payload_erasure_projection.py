"""Tests for the evidence payload erasure projection (ES-065, ADR-017 §5).

The investigation tombstone written by ES-064 **is** the durable erasure intent;
this projector drains it into the object store. Deterministic, in-memory: the
pending set comes from erased investigations' evidence that still carries a
content address, erasure is idempotent, completion redacts the address so the
projection converges, and a store outage leaves the item pending.
"""

import asyncio
from datetime import UTC, datetime

from app.application.investigation import (
    EvidencePayloadErasureProjector,
    InvestigationService,
    payload_address,
)
from app.application.investigation.errors import (
    EvidencePayloadStoreUnavailableError,
)
from app.domain.enums import InvestigationStatus
from app.domain.erasure import REDACTED
from app.domain.identifiers import InvestigationId
from tests.support.builders import build_evidence, build_investigation
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
_CONTENT = b"raw personal payload bytes"


class _UnavailableStore(InMemoryEvidencePayloadStore):
    async def erase(self, address: str) -> None:
        raise EvidencePayloadStoreUnavailableError("store down")


async def _erased_investigation_with_payload(
    payloads: InMemoryEvidencePayloadStore,
    evidence: InMemoryEvidenceRepository,
) -> str:
    """Seed an erased investigation whose evidence references stored bytes."""

    investigations = InMemoryInvestigationRepository()
    service = InvestigationService(
        investigations,
        evidence,
        InMemoryFindingRepository(),
        InMemoryReportRepository(),
        InMemoryOutcomeRepository(),
        InMemoryTraceRepository(),
        payloads=payloads,
    )
    await investigations.add(
        build_investigation(
            "inv-1", status=InvestigationStatus.ACTIVE, created_at=_NOW
        )
    )
    address = payload_address(_CONTENT)
    await payloads.put(address, _CONTENT)
    await service.attach_evidence(
        build_evidence("ev-1", "inv-1", integrity=address)
    )
    await service.erase(InvestigationId("inv-1"), _ERASED_AT)
    return address


def test_projection_erases_bytes_marks_done_and_converges() -> None:
    async def scenario() -> None:
        payloads = InMemoryEvidencePayloadStore()
        evidence = InMemoryEvidenceRepository()
        address = await _erased_investigation_with_payload(payloads, evidence)
        projector = EvidencePayloadErasureProjector(evidence, payloads)

        # The tombstone still references the bytes: exactly one pending item.
        assert len(await evidence.list_pending_payload_erasures(100)) == 1

        assert await projector.project_pending() == 1

        # Bytes gone, address redacted to the erasure marker.
        assert await payloads.get(address) is None
        (item,) = await evidence.list_for_investigation(
            InvestigationId("inv-1")
        )
        assert item.integrity.value == REDACTED

        # Converged: nothing pending, a second run is a no-op.
        assert await evidence.list_pending_payload_erasures(100) == ()
        assert await projector.project_pending() == 0

    asyncio.run(scenario())


def test_live_investigation_payloads_are_never_pending() -> None:
    async def scenario() -> None:
        payloads = InMemoryEvidencePayloadStore()
        evidence = InMemoryEvidenceRepository()
        investigations = InMemoryInvestigationRepository()
        service = InvestigationService(
            investigations,
            evidence,
            InMemoryFindingRepository(),
            InMemoryReportRepository(),
            InMemoryOutcomeRepository(),
            InMemoryTraceRepository(),
            payloads=payloads,
        )
        await investigations.add(
            build_investigation(
                "inv-live", status=InvestigationStatus.ACTIVE, created_at=_NOW
            )
        )
        address = payload_address(_CONTENT)
        await payloads.put(address, _CONTENT)
        await service.attach_evidence(
            build_evidence("ev-live", "inv-live", integrity=address)
        )

        projector = EvidencePayloadErasureProjector(evidence, payloads)
        assert await projector.project_pending() == 0
        # A live investigation's payload is untouched.
        assert await payloads.get(address) == _CONTENT

    asyncio.run(scenario())


def test_store_outage_leaves_the_item_pending() -> None:
    async def scenario() -> None:
        payloads = _UnavailableStore()
        evidence = InMemoryEvidenceRepository()
        await _erased_investigation_with_payload(payloads, evidence)
        projector = EvidencePayloadErasureProjector(evidence, payloads)

        # Failure is contained: nothing completes, the intent survives.
        assert await projector.project_pending() == 0
        assert len(await evidence.list_pending_payload_erasures(100)) == 1
        (item,) = await evidence.list_for_investigation(
            InvestigationId("inv-1")
        )
        assert item.integrity.value != REDACTED

    asyncio.run(scenario())


def test_projection_is_idempotent_when_bytes_are_already_gone() -> None:
    async def scenario() -> None:
        payloads = InMemoryEvidencePayloadStore()
        evidence = InMemoryEvidenceRepository()
        address = await _erased_investigation_with_payload(payloads, evidence)
        # The bytes vanished out of band (an earlier crashed run).
        await payloads.erase(address)

        projector = EvidencePayloadErasureProjector(evidence, payloads)
        assert await projector.project_pending() == 1
        assert await evidence.list_pending_payload_erasures(100) == ()

    asyncio.run(scenario())
