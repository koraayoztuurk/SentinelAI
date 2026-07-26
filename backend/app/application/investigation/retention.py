"""Retention enforcement (ES-070, data-lifecycle.md §3).

Milestone F delivered erasure as a **path**; this makes it happen on its own.
The distinction the architecture draws is preserved exactly: retention
*durations* are deployment policy, while the existence of an enforcement path
is architecture. So this component decides nothing about how long anything is
kept — it is told a cutoff and erases what lies beyond it.

Two properties are deliberate:

- **It introduces no erasure semantics.** The sweep calls the same
  ``InvestigationService.erase`` an analyst's request calls (ES-064), so
  tombstoning, the scoped cascade, idempotence and the secondary-store
  projections are identical whether erasure was requested or expired. An
  automated destructive path that behaved even slightly differently from the
  manual one would be the worst possible place for a divergence.
- **It is bounded per cycle.** A sweep erases at most ``batch_size``
  investigations and reports what it did; a backlog drains over several
  cycles instead of one cycle holding a long transaction over the whole
  history.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from app.application.investigation.errors import InvestigationNotFoundError
from app.application.investigation.service import InvestigationService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetentionSweepOutcome:
    """What one sweep cycle did.

    Returned rather than logged-and-forgotten so the composition root can turn
    it into metrics without the application layer importing observability.
    ``failed`` counts investigations the sweep could not erase this cycle —
    they remain expired and are retried next cycle, so a persistent value is
    the signal that retention is not being enforced.
    """

    erased: int = 0
    failed: int = 0


class RetentionSweeper:
    """Erases investigations whose retention period has passed."""

    def __init__(
        self, investigations: InvestigationService, *, batch_size: int = 50
    ) -> None:
        self._investigations = investigations
        self._batch_size = batch_size

    async def sweep(
        self, created_before: datetime, erased_at: datetime
    ) -> RetentionSweepOutcome:
        """Erase up to one batch of investigations older than the cutoff.

        Both timestamps are caller-supplied: the cutoff expresses the
        deployment's retention policy, and ``erased_at`` stamps the tombstones
        — the same value for every investigation in the cycle, so one sweep
        reads as one event rather than as a scatter of near-identical times.
        """

        expired = await self._investigations.list_expired(
            created_before, self._batch_size
        )
        erased = 0
        failed = 0
        for investigation in expired:
            try:
                await self._investigations.erase(investigation.id, erased_at)
            except InvestigationNotFoundError:
                # Erased or removed between the query and the erase — the
                # outcome the sweep wanted, reached by someone else.
                continue
            except Exception:
                # One poisonous investigation must not stop the sweep: the
                # rest of the batch is still owed its erasure.
                logger.exception(
                    "retention sweep failed for investigation id=%s",
                    investigation.id.value,
                )
                failed += 1
                continue
            erased += 1
        if erased or failed:
            logger.info(
                "retention sweep erased=%d failed=%d cutoff=%s",
                erased,
                failed,
                created_before.isoformat(),
            )
        return RetentionSweepOutcome(erased=erased, failed=failed)
