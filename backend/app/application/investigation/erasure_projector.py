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

**No dead-letter here, deliberately (ES-067).** The embedding projector retires
a hopeless record into a dead-letter state, because a missing embedding is a
degraded search experience. An unerased payload is different in kind: the
platform has been told to destroy personal data (data-lifecycle §3, ADR-017),
and "we gave up" is not an available outcome. So this projection retries
indefinitely — the ES-065 behavior, kept on purpose — and the cycle *reports*
what it could not erase so a stuck erasure becomes operationally visible
(data-lifecycle §5 keeps erasure auditable) instead of quietly terminal.
"""

import logging
from dataclasses import dataclass

from app.application.investigation.errors import (
    EvidencePayloadStoreUnavailableError,
)
from app.application.investigation.payload_store import EvidencePayloadStore
from app.application.investigation.repositories import EvidenceRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ErasureProjectionOutcome:
    """What one erasure cycle did (operational visibility, ES-067).

    ``deferred`` counts payloads still owed after this cycle — a number that
    stays above zero across cycles means erasure is stuck and needs an
    operator, which is exactly what must never be silent.
    """

    erased: int = 0
    deferred: int = 0


class EvidencePayloadErasureProjector:
    """Erases the payload bytes owed by investigation tombstones."""

    def __init__(
        self, evidence: EvidenceRepository, payloads: EvidencePayloadStore
    ) -> None:
        self._evidence = evidence
        self._payloads = payloads

    async def project_pending(self, limit: int = 100) -> ErasureProjectionOutcome:
        """Erase all pending payloads once; report erased and still-owed counts."""

        pending = await self._evidence.list_pending_payload_erasures(limit)
        erased = deferred = 0
        for item in pending:
            address = item.integrity.value
            try:
                await self._payloads.erase(address)
            except EvidencePayloadStoreUnavailableError:
                # The address stays in place: still pending, retried next cycle.
                deferred += 1
                logger.warning(
                    "payload erasure deferred evidence_id=%s", item.id.value
                )
                continue
            await self._evidence.mark_payload_erased(item.id)
            erased += 1
            logger.info(
                "payload erased for tombstone evidence_id=%s", item.id.value
            )
        return ErasureProjectionOutcome(erased, deferred)
