"""Retention sweep background runner (ES-070, data-lifecycle.md §3).

The in-process scheduler that turns the retention *duration* a deployment
configured into erasures actually happening. Composed at the root because it
needs the persistence registry and the clock, neither of which the application
layer may reach.

**Disabled unless a duration is configured.** No default retention period is
architecturally correct, and a sweep is destructive: erasing an analyst's
investigations because nobody chose a number would be the worst kind of
helpful. ``RETENTION_INVESTIGATION_DAYS=0`` — the default — starts nothing.

The runner owns the clock and the observability half; the sweeper owns the
decision and returns what it did, so the application layer never imports the
metrics registry (the ES-067 projector arrangement, reused).

Single-instance by design: several instances would each sweep, which is
*safe* — erasure is idempotent and the query excludes tombstones — but
wasteful. Leader election rides with the post-release multi-instance work.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.investigation import InvestigationService
from app.application.investigation.retention import RetentionSweeper
from app.config.settings import Settings
from app.infrastructure.persistence.postgres.investigation.repositories import (
    PostgresEvidenceRepository,
    PostgresFindingRepository,
    PostgresInvestigationRepository,
    PostgresOutcomeRepository,
    PostgresReportRepository,
    PostgresTraceRepository,
)
from app.infrastructure.persistence.postgres.session import session_scope
from app.infrastructure.persistence.registry import PersistenceRegistry
from app.observability.metrics import metrics

logger = logging.getLogger(__name__)


def start_retention_sweeper(
    registry: PersistenceRegistry, settings: Settings
) -> asyncio.Task[None] | None:
    """Start the retention sweep task, or ``None`` when no duration is set."""

    if settings.retention_investigation_days <= 0:
        return None
    logger.info(
        "retention sweep enabled: investigations older than %d days",
        settings.retention_investigation_days,
    )
    return asyncio.create_task(_run(registry, settings))


async def _run(registry: PersistenceRegistry, settings: Settings) -> None:
    retention = timedelta(days=settings.retention_investigation_days)
    while True:
        try:
            now = datetime.now(UTC)
            async with session_scope(registry.session_factory) as session:
                sweeper = RetentionSweeper(
                    _investigation_service(session),
                    batch_size=settings.retention_sweep_batch_size,
                )
                outcome = await sweeper.sweep(now - retention, now)
            metrics.record_retention_sweep(outcome.erased, outcome.failed)
        except Exception as exc:  # noqa: BLE001 - best-effort background loop
            # Expired investigations stay expired and are swept next cycle;
            # CancelledError is a BaseException, so shutdown is not swallowed.
            logger.warning(
                "retention sweep cycle failed: %s", type(exc).__name__
            )
        await asyncio.sleep(settings.retention_sweep_interval_seconds)


def _investigation_service(session: AsyncSession) -> InvestigationService:
    """Build the Investigation Service over one sweep session.

    The sweep erases through the *same* service operation an analyst's request
    uses (ES-064) — an automated destructive path that behaved differently
    from the manual one would be the worst place for a divergence.
    """

    return InvestigationService(
        PostgresInvestigationRepository(session),
        PostgresEvidenceRepository(session),
        PostgresFindingRepository(session),
        PostgresReportRepository(session),
        PostgresOutcomeRepository(session),
        PostgresTraceRepository(session),
    )
