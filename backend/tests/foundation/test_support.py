"""Foundation tests (ES-032).

Exercise the shared test support so the foundation infrastructure is itself
validated (not speculative) and demonstrate the reuse pattern for later validation
specs. Marked ``unit`` (Domain Validation, testing-strategy §5); async behaviour is
driven through ``asyncio.run``.
"""

import asyncio

import pytest

from tests.support.builders import (
    FIXED_TIME,
    build_evidence,
    build_finding,
    build_investigation,
    build_report,
    make_investigation_service,
)
from tests.support.doubles import FixedClock, SequentialIdGenerator


@pytest.mark.unit
def test_shared_doubles_drive_the_investigation_service() -> None:
    service = make_investigation_service()

    async def scenario() -> None:
        investigation = build_investigation("inv-1")
        await service.create(investigation)

        fetched = await service.get(investigation.id)
        assert fetched.id == investigation.id

        await service.attach_evidence(build_evidence("ev-1", "inv-1"))
        evidence = await service.list_evidence(investigation.id)
        assert [e.id.value for e in evidence] == ["ev-1"]

    asyncio.run(scenario())


@pytest.mark.unit
def test_builders_construct_valid_domain_objects() -> None:
    finding = build_finding("fnd-1", "inv-1", supporting_evidence=("ev-1",))
    assert finding.id.value == "fnd-1"
    assert [e.value for e in finding.supporting_evidence] == ["ev-1"]

    report = build_report("rpt-1", "inv-1", version=2)
    assert report.version == 2


@pytest.mark.unit
def test_builders_return_independent_objects() -> None:
    first = build_investigation("inv-1")
    second = build_investigation("inv-1")
    assert first is not second


@pytest.mark.unit
def test_sequential_id_generator_is_deterministic() -> None:
    generator = SequentialIdGenerator()
    assert [generator.new_id() for _ in range(3)] == ["id-1", "id-2", "id-3"]
    assert SequentialIdGenerator("ev").new_id() == "ev-1"


@pytest.mark.unit
def test_fixed_clock_returns_the_configured_instant() -> None:
    assert FixedClock(FIXED_TIME).now() == FIXED_TIME
