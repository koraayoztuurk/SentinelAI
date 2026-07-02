"""Scalability Validation (ES-036, performance-reliability §5).

Verifies that the architectural capabilities preserve their intended behavior
under concurrent use: concurrent service operations stay isolated and
consistent (the services are stateless over repository-driven state) and
concurrent metric recording never loses an observation (the registry is safe
under contention, including while rendering). Architectural assurance at small
scale — not load testing or benchmarking (performance-reliability §3).
"""

import asyncio
import threading

import pytest

from app.domain.identifiers import InvestigationId
from app.observability.metrics import PlatformMetrics
from tests.support.builders import build_investigation, make_investigation_service

pytestmark = pytest.mark.operational


def test_concurrent_service_operations_stay_isolated() -> None:
    """Fifty concurrent creates succeed and each remains individually readable."""

    async def scenario() -> None:
        service = make_investigation_service()

        await asyncio.gather(
            *(
                service.create(build_investigation(f"inv-{index}"))
                for index in range(50)
            )
        )

        fetched = await asyncio.gather(
            *(service.get(InvestigationId(f"inv-{index}")) for index in range(50))
        )
        assert {inv.id.value for inv in fetched} == {
            f"inv-{index}" for index in range(50)
        }

    asyncio.run(scenario())


def test_concurrent_metric_recording_loses_no_observation() -> None:
    """Contended recording (with interleaved rendering) stays exact."""

    registry = PlatformMetrics()
    threads_count = 8
    records_per_thread = 250

    def record() -> None:
        for _ in range(records_per_thread):
            registry.record_request("GET", 200, 1.0)

    def render_repeatedly() -> None:
        for _ in range(50):
            registry.render()

    workers = [threading.Thread(target=record) for _ in range(threads_count)]
    workers.append(threading.Thread(target=render_repeatedly))
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    expected = threads_count * records_per_thread
    rendered = registry.render()
    assert (
        f'sentinelai_requests_total{{method="GET",status="200"}} {expected}'
        in rendered
    )
    assert f"sentinelai_request_duration_ms_count {expected}" in rendered
