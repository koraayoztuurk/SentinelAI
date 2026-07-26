"""Tests for retention enforcement (ES-070, data-lifecycle.md §3).

The sweep is the platform's only **automated destructive** path, so these
tests are about restraint as much as about function: that it erases exactly
what is past the cutoff, that it uses the same erase path a request uses, that
it converges instead of revisiting its own tombstones, and that one bad
investigation cannot stop the rest of the batch from being erased.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.application.investigation.errors import InvestigationNotFoundError
from app.application.investigation.retention import (
    RetentionSweeper,
    RetentionSweepOutcome,
)
from app.domain.identifiers import InvestigationId
from app.domain.investigation import Investigation
from tests.support.builders import build_investigation

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 7, 26, tzinfo=UTC)


class _Investigations:
    """Investigation Service double recording what the sweep erased."""

    def __init__(
        self, expired: tuple[Investigation, ...], *, failing: str | None = None
    ) -> None:
        self._expired = expired
        self._failing = failing
        self.erased: list[str] = []
        self.cutoffs: list[datetime] = []

    async def list_expired(
        self, created_before: datetime, limit: int
    ) -> tuple[Investigation, ...]:
        self.cutoffs.append(created_before)
        return self._expired[:limit]

    async def erase(
        self, investigation_id: InvestigationId, erased_at: datetime
    ) -> Investigation:
        if investigation_id.value == self._failing:
            raise RuntimeError("store unavailable")
        if investigation_id.value == "vanished":
            raise InvestigationNotFoundError("gone")
        self.erased.append(investigation_id.value)
        return _investigation(investigation_id.value)


def _investigation(identifier: str) -> Investigation:
    return build_investigation(
        identifier, created_at=_NOW - timedelta(days=400)
    )


def _sweeper(
    service: _Investigations, *, batch_size: int = 50
) -> RetentionSweeper:
    return RetentionSweeper(service, batch_size=batch_size)  # type: ignore[arg-type]


def _sweep(
    service: _Investigations, *, batch_size: int = 50, retention_days: int = 365
) -> RetentionSweepOutcome:
    sweeper = _sweeper(service, batch_size=batch_size)
    return asyncio.run(
        sweeper.sweep(_NOW - timedelta(days=retention_days), _NOW)
    )


def test_expired_investigations_are_erased() -> None:
    service = _Investigations(
        (_investigation("inv-1"), _investigation("inv-2"))
    )

    outcome = _sweep(service)

    assert service.erased == ["inv-1", "inv-2"]
    assert outcome == RetentionSweepOutcome(erased=2, failed=0)


def test_the_cutoff_is_the_configured_retention_window() -> None:
    # The duration is deployment policy: the sweeper is *told* the cutoff and
    # never computes a retention period of its own.
    service = _Investigations(())

    _sweep(service, retention_days=30)

    assert service.cutoffs == [_NOW - timedelta(days=30)]


def test_nothing_expired_means_nothing_erased() -> None:
    service = _Investigations(())

    outcome = _sweep(service)

    assert service.erased == []
    assert outcome == RetentionSweepOutcome()


def test_a_cycle_erases_at_most_one_batch() -> None:
    # A backlog drains over several cycles rather than one cycle holding a
    # long transaction over the whole history.
    service = _Investigations(
        tuple(_investigation(f"inv-{index}") for index in range(10))
    )

    outcome = _sweep(service, batch_size=3)

    assert outcome.erased == 3
    assert service.erased == ["inv-0", "inv-1", "inv-2"]


def test_one_failure_does_not_abandon_the_rest_of_the_batch() -> None:
    # The other investigations are still owed their erasure — a retention
    # obligation is per investigation, not per cycle.
    service = _Investigations(
        (
            _investigation("inv-1"),
            _investigation("poison"),
            _investigation("inv-3"),
        ),
        failing="poison",
    )

    outcome = _sweep(service)

    assert service.erased == ["inv-1", "inv-3"]
    assert outcome == RetentionSweepOutcome(erased=1 + 1, failed=1)


def test_an_investigation_erased_concurrently_is_not_a_failure() -> None:
    # Someone else reaching the outcome the sweep wanted is success, not an
    # error to report and retry forever.
    service = _Investigations(
        (_investigation("vanished"), _investigation("inv-2"))
    )

    outcome = _sweep(service)

    assert service.erased == ["inv-2"]
    assert outcome == RetentionSweepOutcome(erased=1, failed=0)
