"""Evidence payload store port and content addressing (ES-060, ADR-015).

Raw evidence payloads live in a content-addressed store (database-architecture
§8b); the Evidence record references its payload by content address — the
integrity hash, which is also the verifiable integrity anchor (Domain Rule
1/9). The **application owns the address scheme** (``sha256:<64 lowercase
hex>``): an address is a deterministic derivation from the payload bytes,
never a generated identifier, so the caller-supplies-identifiers discipline is
unaffected and adapters never mint anything.

The port is minimal (ADR-015 §3): exactly the operations the owning
Investigation Service needs. ``put`` is idempotent (content addressing makes
re-storing existing content a no-op); ``get`` returns ``None`` when the
address does not resolve so dangling references stay observable (§8a) —
adapters raise :class:`~app.application.investigation.errors.
EvidencePayloadStoreUnavailableError` only for operational store failures.
"""

import hashlib
import re
from typing import Protocol

# The address prefix marks an integrity value as a payload content address;
# anything else is an opaque interim integrity value (§8b inline state).
PAYLOAD_ADDRESS_PREFIX = "sha256:"

_ADDRESS = re.compile(r"^sha256:[0-9a-f]{64}$")


def payload_address(content: bytes) -> str:
    """Compute the content address of a payload (application-owned scheme)."""

    return f"{PAYLOAD_ADDRESS_PREFIX}{hashlib.sha256(content).hexdigest()}"


def is_payload_address(value: str) -> bool:
    """Return whether the value is a well-formed payload content address."""

    return _ADDRESS.fullmatch(value) is not None


class EvidencePayloadStore(Protocol):
    """Replaceable content-addressed payload store (ADR-015)."""

    async def put(self, address: str, content: bytes) -> None: ...

    async def get(self, address: str) -> bytes | None: ...

    async def exists(self, address: str) -> bool: ...

    async def erase(self, address: str) -> None:
        """Render the payload at this address unrecoverable (ADR-017 §6).

        The end-of-life operation (data-lifecycle.md §4). Idempotent: erasing an
        address that resolves to nothing — already erased, never stored, or
        malformed — is a no-op, so the erasure projection is safely retriable.
        The strategy is the adapter's choice: physical deletion for the dev-grade
        filesystem store, crypto-shredding for the immutable production object
        store (Milestone G).
        """
        ...
