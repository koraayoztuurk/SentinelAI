"""Tests for the crypto-shredding payload store (ES-070, ADR-017 §6).

The strategy exists for a store that cannot promise deletion, so the property
under test is not "the bytes are gone" but **"the bytes are unreadable even
when they are still there"**. The double therefore keeps everything it is
given and never forgets anything unless asked — a deliberately unhelpful
backend, which is exactly what an immutable production bucket is.
"""

import asyncio

import pytest

from app.application.investigation.payload_store import payload_address
from app.infrastructure.objectstore import CryptoShredPayloadStore

pytestmark = pytest.mark.unit

_CONTENT = b"exported mailbox: alice@example.com"


class _Store:
    """In-memory payload store double."""

    def __init__(self, *, refuse_erase: bool = False) -> None:
        self.objects: dict[str, bytes] = {}
        self._refuse_erase = refuse_erase

    async def put(self, address: str, content: bytes) -> None:
        self.objects.setdefault(address, content)

    async def get(self, address: str) -> bytes | None:
        return self.objects.get(address)

    async def exists(self, address: str) -> bool:
        return address in self.objects

    async def erase(self, address: str) -> None:
        if self._refuse_erase:
            # An immutable / WORM bucket: the reason this strategy exists.
            raise RuntimeError("object storage is immutable")
        self.objects.pop(address, None)


def _shredding(
    payloads: _Store, keys: _Store
) -> CryptoShredPayloadStore:
    return CryptoShredPayloadStore(payloads, keys)  # type: ignore[arg-type]


def _address() -> str:
    return payload_address(_CONTENT)


def test_a_stored_payload_reads_back_intact() -> None:
    async def scenario() -> None:
        payloads, keys = _Store(), _Store()
        store = _shredding(payloads, keys)
        address = _address()

        await store.put(address, _CONTENT)

        assert await store.get(address) == _CONTENT

    asyncio.run(scenario())


def test_the_stored_bytes_are_not_the_payload() -> None:
    # If the ciphertext contained the plaintext, shredding the key would
    # protect nothing.
    async def scenario() -> None:
        payloads, keys = _Store(), _Store()
        address = _address()

        await _shredding(payloads, keys).put(address, _CONTENT)

        stored = payloads.objects[address]
        assert _CONTENT not in stored
        assert b"alice@example.com" not in stored

    asyncio.run(scenario())


def test_shredding_makes_surviving_bytes_unreadable() -> None:
    # The whole point: a backend that refuses to delete still cannot serve the
    # payload once its key is destroyed.
    async def scenario() -> None:
        payloads, keys = _Store(refuse_erase=True), _Store()
        store = _shredding(payloads, keys)
        address = _address()
        await store.put(address, _CONTENT)

        await store.erase(address)

        assert payloads.objects[address]  # the bytes are still there …
        assert await store.get(address) is None  # … and unreadable
        assert await store.exists(address) is False

    asyncio.run(scenario())


def test_shredding_releases_the_bytes_when_the_backend_allows_it() -> None:
    async def scenario() -> None:
        payloads, keys = _Store(), _Store()
        store = _shredding(payloads, keys)
        address = _address()
        await store.put(address, _CONTENT)

        await store.erase(address)

        assert payloads.objects == {}
        assert keys.objects == {}

    asyncio.run(scenario())


def test_shredding_is_idempotent() -> None:
    # The erasure projection retries; a second shred must be a no-op rather
    # than an error that keeps the projection pending forever (ADR-017 §5).
    async def scenario() -> None:
        store = _shredding(_Store(), _Store())
        address = _address()
        await store.put(address, _CONTENT)

        await store.erase(address)
        await store.erase(address)
        await store.erase(payload_address(b"never stored"))

        assert await store.get(address) is None

    asyncio.run(scenario())


def test_a_tampered_payload_is_refused_rather_than_returned() -> None:
    # Authenticated encryption: corrupted evidence is worse than absent
    # evidence, because it still looks like evidence.
    async def scenario() -> None:
        payloads, keys = _Store(), _Store()
        store = _shredding(payloads, keys)
        address = _address()
        await store.put(address, _CONTENT)

        sealed = bytearray(payloads.objects[address])
        sealed[0] ^= 0xFF
        payloads.objects[address] = bytes(sealed)

        assert await store.get(address) is None

    asyncio.run(scenario())


def test_a_payload_moved_to_another_address_is_refused() -> None:
    # The address is bound into the encryption, so ciphertext relocated under
    # a different address does not decrypt — content addressing stays
    # meaningful rather than becoming a filing convention.
    async def scenario() -> None:
        payloads, keys = _Store(), _Store()
        store = _shredding(payloads, keys)
        address = _address()
        other = payload_address(b"different content")
        await store.put(address, _CONTENT)

        payloads.objects[other] = payloads.objects[address]
        keys.objects[other] = keys.objects[address]

        assert await store.get(other) is None

    asyncio.run(scenario())


def test_missing_key_material_reads_as_absent() -> None:
    async def scenario() -> None:
        payloads, keys = _Store(), _Store()
        store = _shredding(payloads, keys)
        address = _address()
        await store.put(address, _CONTENT)
        keys.objects[address] = b"too short"

        assert await store.get(address) is None

    asyncio.run(scenario())


def test_restoring_the_same_content_keeps_its_existing_key() -> None:
    # Content addressing means a re-upload targets the same object; minting a
    # second key would orphan the ciphertext the first one unlocks.
    async def scenario() -> None:
        payloads, keys = _Store(), _Store()
        store = _shredding(payloads, keys)
        address = _address()
        await store.put(address, _CONTENT)
        original_key = keys.objects[address]

        await store.put(address, _CONTENT)

        assert keys.objects[address] == original_key
        assert await store.get(address) == _CONTENT

    asyncio.run(scenario())
