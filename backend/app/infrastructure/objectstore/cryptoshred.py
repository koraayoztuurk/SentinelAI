"""Crypto-shredding evidence payload store (ES-070, ADR-015 §6 / ADR-017 §6).

The erasure strategy the architecture designates for the **production** payload
store. It exists because of a property of production object storage the dev
adapter does not have: an immutable, versioned or backed-up bucket cannot
promise that deleting an object destroys its bytes. Crypto-shredding sidesteps
that promise entirely — the payload is stored encrypted, and erasure destroys
the **key**. Whatever survives in an immutable tier, a snapshot or a backup is
then unrecoverable ciphertext.

The design is a composition rather than a new backend:

- payload bytes and keys live in **two separate stores of the same kind**, so
  a deployment can give them different storage classes — the payload tier
  immutable and backed up, the key tier mutable and *excluded from backups*.
  That separation is the entire security argument: shredding is only real if
  the key tier can actually forget.
- both are ``EvidencePayloadStore`` implementations, so this adapter composes
  the existing filesystem store today and an S3-compatible one tomorrow with
  **no port change** anywhere (ADR-015's port is unchanged).

AES-256-GCM: authenticated encryption, so a tampered ciphertext fails to
decrypt rather than returning corrupted evidence — the integrity property
evidence most needs.

**A caveat this does not remove.** Addresses are content hashes (ADR-015 §2),
so two evidence items holding byte-identical payloads share one address, one
key and therefore one fate: erasing for one erases for both. Per-erasure-unit
keys cannot fix this while the object identity *is* the content — that would
need a non-content-derived address, which is a deliberate ADR-015 decision
rather than an oversight here. The caveat is unchanged from the filesystem
adapter (ES-065) and is recorded rather than papered over.
"""

import logging
import os
from collections.abc import Callable

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.application.investigation.payload_store import EvidencePayloadStore

logger = logging.getLogger(__name__)

_KEY_BYTES = 32  # AES-256
_NONCE_BYTES = 12  # GCM standard nonce length


class CryptoShredPayloadStore:
    """``EvidencePayloadStore`` that erases by destroying the key."""

    def __init__(
        self,
        payloads: EvidencePayloadStore,
        keys: EvidencePayloadStore,
        *,
        generate_key: Callable[[], bytes] = lambda: os.urandom(_KEY_BYTES),
        generate_nonce: Callable[[], bytes] = lambda: os.urandom(_NONCE_BYTES),
    ) -> None:
        self._payloads = payloads
        self._keys = keys
        self._generate_key = generate_key
        self._generate_nonce = generate_nonce

    async def put(self, address: str, content: bytes) -> None:
        """Encrypt and store the payload, and store its key.

        The key is written **first**. A crash between the two writes then
        leaves an unused key — harmless — rather than ciphertext nobody can
        ever read, which would occupy an immutable tier forever.

        Idempotent like the stores it composes: an address already holding a
        key keeps it, so re-uploading identical content does not silently
        orphan the ciphertext its existing key unlocks.
        """

        existing = await self._keys.get(address)
        if existing is not None and await self._payloads.exists(address):
            return
        key = self._generate_key()
        nonce = self._generate_nonce()
        sealed = AESGCM(key).encrypt(nonce, content, address.encode())
        await self._keys.put(address, key + nonce)
        await self._payloads.put(address, sealed)

    async def get(self, address: str) -> bytes | None:
        """Return the decrypted payload, or ``None`` if it cannot be read.

        A shredded payload is indistinguishable from an absent one *at this
        boundary* — which is correct: the explicit "erased" state of an
        evidence reference is carried by its tombstone in the authoritative
        store (§8a), not inferred from the object store.
        """

        material = await self._keys.get(address)
        sealed = await self._payloads.get(address)
        if material is None or sealed is None:
            return None
        if len(material) != _KEY_BYTES + _NONCE_BYTES:
            logger.warning("payload key material is malformed")
            return None
        key, nonce = material[:_KEY_BYTES], material[_KEY_BYTES:]
        try:
            return AESGCM(key).decrypt(nonce, sealed, address.encode())
        except InvalidTag:
            # Authenticated encryption: a tampered or truncated payload is
            # refused rather than returned as corrupted evidence.
            logger.warning("payload failed authentication at address")
            return None

    async def exists(self, address: str) -> bool:
        """Whether the payload is still readable — key **and** ciphertext."""

        return await self._keys.exists(address) and await self._payloads.exists(
            address
        )

    async def erase(self, address: str) -> None:
        """Shred the payload: destroy the key, then release the bytes.

        Destroying the key is what makes the payload unrecoverable, so it
        happens first and its failure is the operation's failure. Removing the
        ciphertext afterwards is housekeeping: a production bucket may refuse
        it (that is *why* this strategy exists), so its failure is contained
        rather than reported as a failed erasure.

        Idempotent: shredding an address that resolves to nothing is a no-op,
        which keeps the erasure projection safely retriable (ADR-017 §5).
        """

        await self._keys.erase(address)
        try:
            await self._payloads.erase(address)
        except Exception:  # noqa: BLE001 - the bytes are already unreadable
            logger.warning(
                "payload bytes could not be removed after shredding; "
                "they are unrecoverable without their key"
            )
