"""Evidence payload erasure projector (ES-065, ADR-017 §5).

The asynchronous, idempotent projector owned by the Investigation Service's
layer: it physically erases the payload bytes of erased investigations from the
content-addressed object store.

The **erasure intent is the tombstone itself** — written in the same local
transaction as the investigation's erasure (ES-064), so no erasure operation
ever writes two stores (AC-14). This projector drains that intent: evidence
tombstones of erased investigations that still carry an address-shaped integrity
value have bytes that may still exist; each is erased in the object store and
then marked done by redacting the address.

Guarantees (ADR-012, reused for end-of-life):

- **Idempotent** — the store's ``erase`` is a no-op for an address that resolves
  to nothing, so re-running after a crash is harmless.
- **Convergent** — marking done redacts the address, so a completed item stops
  being pending; the projection drains to empty.
- **Failure isolation** — a store outage leaves the address in place, so the
  item stays pending and observable for the next cycle; the authoritative
  tombstone is never touched.
- **No layer violation** — depends only on application ports (evidence
  repository, payload store); the concrete adapters are injected.
"""

import logging

from app.application.investigation.errors import (
    EvidencePayloadStoreUnavailableError,
)
from app.application.investigation.payload_store import EvidencePayloadStore
from app.application.investigation.repositories import EvidenceRepository

logger = logging.getLogger(__name__)


class EvidencePayloadErasureProjector:
    """Erases the payload bytes owed by investigation tombstones."""

    def __init__(
        self, evidence: EvidenceRepository, payloads: EvidencePayloadStore
    ) -> None:
        self._evidence = evidence
        self._payloads = payloads

    async def project_pending(self, limit: int = 100) -> int:
        """Erase all pending payloads once; return how many were completed."""

        pending = await self._evidence.list_pending_payload_erasures(limit)
        erased = 0
        for item in pending:
            address = item.integrity.value
            try:
                await self._payloads.erase(address)
            except EvidencePayloadStoreUnavailableError:
                # The address stays in place: still pending, retried next cycle.
                logger.warning(
                    "payload erasure deferred evidence_id=%s", item.id.value
                )
                continue
            await self._evidence.mark_payload_erased(item.id)
            erased += 1
            logger.info(
                "payload erased for tombstone evidence_id=%s", item.id.value
            )
        return erased
