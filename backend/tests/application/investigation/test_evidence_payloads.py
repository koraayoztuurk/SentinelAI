"""Tests for the Investigation Service evidence payload operations (ES-060).

ADR-015: the application owns the address scheme (``sha256:<hex>``), the
Investigation Service mediates every payload access, hash verification runs on
read, and attach-time validation covers only address-shaped integrity values.
In-memory doubles; plain functions, ``asyncio.run``.
"""

import asyncio

import pytest

from app.application.investigation import (
    EvidencePayloadIntegrityError,
    EvidencePayloadMissingError,
    EvidencePayloadNotFoundError,
    EvidencePayloadStoreUnavailableError,
    InvestigationNotFoundError,
    is_payload_address,
    payload_address,
)
from app.domain.identifiers import EvidenceId, InvestigationId
from tests.support.builders import (
    build_evidence,
    build_investigation,
    make_investigation_service,
)
from tests.support.doubles import InMemoryEvidencePayloadStore

_CONTENT = b"raw log archive bytes"


# ----------------------------------------------------------------- addressing


def test_payload_address_is_deterministic_sha256() -> None:
    address = payload_address(_CONTENT)

    assert address == payload_address(_CONTENT)
    assert address.startswith("sha256:")
    assert is_payload_address(address)


def test_is_payload_address_rejects_malformed_values() -> None:
    assert not is_payload_address("verified")
    assert not is_payload_address("sha256:short")
    assert not is_payload_address("sha256:" + "Z" * 64)
    assert not is_payload_address("sha256:../../../etc/passwd")


# ---------------------------------------------------------------------- store


def test_store_payload_returns_content_address() -> None:
    async def scenario() -> None:
        store = InMemoryEvidencePayloadStore()
        service = make_investigation_service(payloads=store)
        await service.create(build_investigation("inv-1"))

        address = await service.store_evidence_payload(
            InvestigationId("inv-1"), _CONTENT
        )

        assert address == payload_address(_CONTENT)
        assert await store.get(address) == _CONTENT

    asyncio.run(scenario())


def test_store_payload_requires_existing_investigation() -> None:
    async def scenario() -> None:
        service = make_investigation_service(
            payloads=InMemoryEvidencePayloadStore()
        )

        with pytest.raises(InvestigationNotFoundError):
            await service.store_evidence_payload(
                InvestigationId("ghost"), _CONTENT
            )

    asyncio.run(scenario())


def test_store_payload_without_composed_store_is_unavailable() -> None:
    async def scenario() -> None:
        service = make_investigation_service()
        await service.create(build_investigation("inv-1"))

        with pytest.raises(EvidencePayloadStoreUnavailableError):
            await service.store_evidence_payload(
                InvestigationId("inv-1"), _CONTENT
            )

    asyncio.run(scenario())


# ------------------------------------------------------------------- retrieve


def test_get_payload_roundtrip_verified() -> None:
    async def scenario() -> None:
        store = InMemoryEvidencePayloadStore()
        service = make_investigation_service(payloads=store)
        await service.create(build_investigation("inv-1"))
        address = await service.store_evidence_payload(
            InvestigationId("inv-1"), _CONTENT
        )
        await service.attach_evidence(
            build_evidence("ev-1", "inv-1", integrity=address)
        )

        assert await service.get_evidence_payload(EvidenceId("ev-1")) == (
            _CONTENT
        )

    asyncio.run(scenario())


def test_get_payload_for_inline_evidence_is_not_found() -> None:
    async def scenario() -> None:
        service = make_investigation_service(
            payloads=InMemoryEvidencePayloadStore()
        )
        await service.create(build_investigation("inv-1"))
        # The interim inline state: an opaque integrity value, no payload.
        await service.attach_evidence(
            build_evidence("ev-1", "inv-1", integrity="verified")
        )

        with pytest.raises(EvidencePayloadNotFoundError):
            await service.get_evidence_payload(EvidenceId("ev-1"))

    asyncio.run(scenario())


def test_get_payload_dangling_address_is_observable_not_found() -> None:
    async def scenario() -> None:
        store = InMemoryEvidencePayloadStore()
        service = make_investigation_service(payloads=store)
        await service.create(build_investigation("inv-1"))
        address = await service.store_evidence_payload(
            InvestigationId("inv-1"), _CONTENT
        )
        await service.attach_evidence(
            build_evidence("ev-1", "inv-1", integrity=address)
        )
        # The payload disappears out of band (a store fault) — the reference
        # must stay observable (§8a).
        store.remove(address)

        with pytest.raises(EvidencePayloadNotFoundError):
            await service.get_evidence_payload(EvidenceId("ev-1"))

    asyncio.run(scenario())


def test_get_payload_verification_mismatch_is_integrity_error() -> None:
    async def scenario() -> None:
        store = InMemoryEvidencePayloadStore()
        service = make_investigation_service(payloads=store)
        await service.create(build_investigation("inv-1"))
        address = await service.store_evidence_payload(
            InvestigationId("inv-1"), _CONTENT
        )
        await service.attach_evidence(
            build_evidence("ev-1", "inv-1", integrity=address)
        )
        store.corrupt(address, b"tampered bytes")

        with pytest.raises(EvidencePayloadIntegrityError):
            await service.get_evidence_payload(EvidenceId("ev-1"))

    asyncio.run(scenario())


# ------------------------------------------------------- attach-time validation


def test_attach_with_stored_payload_address_succeeds() -> None:
    async def scenario() -> None:
        store = InMemoryEvidencePayloadStore()
        service = make_investigation_service(payloads=store)
        await service.create(build_investigation("inv-1"))
        address = await service.store_evidence_payload(
            InvestigationId("inv-1"), _CONTENT
        )

        attached = await service.attach_evidence(
            build_evidence("ev-1", "inv-1", integrity=address)
        )

        assert attached.integrity.value == address

    asyncio.run(scenario())


def test_attach_with_unstored_address_is_rejected() -> None:
    async def scenario() -> None:
        service = make_investigation_service(
            payloads=InMemoryEvidencePayloadStore()
        )
        await service.create(build_investigation("inv-1"))

        with pytest.raises(EvidencePayloadMissingError):
            await service.attach_evidence(
                build_evidence(
                    "ev-1", "inv-1", integrity=payload_address(b"never stored")
                )
            )

    asyncio.run(scenario())


def test_attach_with_malformed_address_claim_is_rejected() -> None:
    async def scenario() -> None:
        service = make_investigation_service(
            payloads=InMemoryEvidencePayloadStore()
        )
        await service.create(build_investigation("inv-1"))

        # Claims the address prefix but is not a well-formed address.
        with pytest.raises(EvidencePayloadMissingError):
            await service.attach_evidence(
                build_evidence("ev-1", "inv-1", integrity="sha256:nope")
            )

    asyncio.run(scenario())


def test_attach_with_opaque_integrity_stays_untouched() -> None:
    async def scenario() -> None:
        service = make_investigation_service(
            payloads=InMemoryEvidencePayloadStore()
        )
        await service.create(build_investigation("inv-1"))

        attached = await service.attach_evidence(
            build_evidence("ev-1", "inv-1", integrity="verified")
        )

        assert attached.integrity.value == "verified"

    asyncio.run(scenario())


def test_attach_without_composed_store_enforces_nothing() -> None:
    async def scenario() -> None:
        service = make_investigation_service()
        await service.create(build_investigation("inv-1"))

        # No store, no checkable claim — prior behavior preserved.
        attached = await service.attach_evidence(
            build_evidence(
                "ev-1", "inv-1", integrity=payload_address(b"unchecked")
            )
        )

        assert attached.id.value == "ev-1"

    asyncio.run(scenario())
