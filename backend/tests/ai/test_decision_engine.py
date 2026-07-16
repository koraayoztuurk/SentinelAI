"""Tests for the Decision Engine (ES-055).

The engine synthesizes an investigation's confirmed findings into one
``InvestigationOutcome`` over a scripted LLM double: outcome persisted with
parsed fields, skip conditions honored (existing outcome / no confirmed
findings), references outside the confirmed set discarded, confidence
clamped, malformed responses raised — never a fabricated partial outcome.
In-memory doubles, plain functions, ``asyncio.run``.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.ai.agents.planner.state import InvestigationState
from app.ai.decision import DecisionEngine
from app.ai.errors import DecisionEngineError
from app.application.investigation import (
    InvestigationService,
    OutcomeNotFoundError,
)
from app.domain.enums import (
    FindingStatus,
    InvestigationOutcomeStatus,
)
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence
from tests.support.builders import (
    build_evidence,
    build_finding,
    build_investigation,
    make_investigation_service,
)


class ScriptedLLM:
    """Deterministic LLM double returning a fixed response text."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.prompts: list[str] = []

    async def generate(self, request):  # noqa: ANN001, ANN201 - protocol duck
        self.prompts.append(request.prompt)

        class _Response:
            text = self._text

        return _Response()


class SequentialIds:
    def __init__(self) -> None:
        self._count = 0

    def new_id(self) -> str:
        self._count += 1
        return f"out-{self._count}"


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 15, tzinfo=UTC)


def _state(investigation_id: str = "inv-1") -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId(investigation_id),
        status="created",
        confidence=Confidence(0.8),
        objectives=("Investigate: beaconing",),
        knowledge=("[semantic] memory:m-1 (confidence=0.90) beacon pattern",),
    )


async def _service_with_confirmed() -> InvestigationService:
    service = make_investigation_service()
    await service.create(build_investigation("inv-1"))
    await service.attach_evidence(build_evidence("ev-1", "inv-1"))
    await service.create_finding(
        build_finding(
            "f-1",
            "inv-1",
            supporting_evidence=("ev-1",),
            status=FindingStatus.VALIDATED,
            confidence=0.85,
        )
    )
    await service.create_finding(
        build_finding(
            "f-2",
            "inv-1",
            supporting_evidence=("ev-1",),
            status=FindingStatus.PROPOSED,
        )
    )
    return service


_GOOD_RESPONSE = (
    '{"recommendation": "Contain HOST-1 and sinkhole the domain.", '
    '"confidence": 0.82, "contributing_findings": ["f-1"], '
    '"detected_conflicts": ["beacon interval varies"], '
    '"open_questions": ["initial access vector"]}'
)


def _engine(
    service: InvestigationService, text: str = _GOOD_RESPONSE
) -> tuple[DecisionEngine, ScriptedLLM]:
    llm = ScriptedLLM(text)
    return (
        DecisionEngine(llm, service, SequentialIds(), FixedClock()),
        llm,
    )


def test_synthesizes_and_persists_the_outcome() -> None:
    async def scenario() -> None:
        service = await _service_with_confirmed()
        engine, llm = _engine(service)

        outcome = await engine.synthesize(_state())

        assert outcome is not None
        assert outcome.status is InvestigationOutcomeStatus.SYNTHESIZED
        assert outcome.recommendation == (
            "Contain HOST-1 and sinkhole the domain."
        )
        assert outcome.confidence.value == 0.82
        assert [f.value for f in outcome.contributing_findings] == ["f-1"]
        assert outcome.detected_conflicts == ("beacon interval varies",)
        assert outcome.open_questions == ("initial access vector",)
        # Persisted through the service (0..1 read surface, ES-045).
        persisted = await service.get_outcome(InvestigationId("inv-1"))
        assert persisted.id == outcome.id
        # The synthesis prompt derives from the confirmed findings and state.
        prompt = llm.prompts[0]
        assert "f-1" in prompt
        assert "f-2" not in prompt  # proposed findings never contribute
        assert "Investigate: beaconing" in prompt
        assert "beacon pattern" in prompt  # retrieved knowledge observed

    asyncio.run(scenario())


def test_skips_when_an_outcome_already_exists() -> None:
    async def scenario() -> None:
        service = await _service_with_confirmed()
        engine, llm = _engine(service)
        first = await engine.synthesize(_state())
        assert first is not None

        second = await engine.synthesize(_state())

        assert second is None
        # No second provider call was made (skip precedes generation).
        assert len(llm.prompts) == 1

    asyncio.run(scenario())


def test_skips_without_confirmed_findings() -> None:
    async def scenario() -> None:
        service = make_investigation_service()
        await service.create(build_investigation("inv-1"))
        engine, llm = _engine(service)

        outcome = await engine.synthesize(_state())

        assert outcome is None
        assert llm.prompts == []
        with pytest.raises(OutcomeNotFoundError):
            await service.get_outcome(InvestigationId("inv-1"))

    asyncio.run(scenario())


def test_unknown_contributing_references_are_discarded() -> None:
    async def scenario() -> None:
        service = await _service_with_confirmed()
        engine, _ = _engine(
            service,
            '{"recommendation": "r", "confidence": 0.5, '
            '"contributing_findings": ["ghost", "f-1"]}',
        )

        outcome = await engine.synthesize(_state())

        assert outcome is not None
        assert [f.value for f in outcome.contributing_findings] == ["f-1"]

    asyncio.run(scenario())


def test_absent_contributing_selection_attributes_all_confirmed() -> None:
    async def scenario() -> None:
        service = await _service_with_confirmed()
        engine, _ = _engine(
            service, '{"recommendation": "r", "confidence": 0.5}'
        )

        outcome = await engine.synthesize(_state())

        assert outcome is not None
        assert [f.value for f in outcome.contributing_findings] == ["f-1"]

    asyncio.run(scenario())


def test_confidence_is_clamped_to_valid_range() -> None:
    async def scenario() -> None:
        service = await _service_with_confirmed()
        engine, _ = _engine(
            service, '{"recommendation": "r", "confidence": 1.7}'
        )

        outcome = await engine.synthesize(_state())

        assert outcome is not None
        assert outcome.confidence.value == 1.0

    asyncio.run(scenario())


def test_malformed_response_raises_and_persists_nothing() -> None:
    async def scenario() -> None:
        service = await _service_with_confirmed()
        engine, _ = _engine(service, "not json at all")

        with pytest.raises(DecisionEngineError):
            await engine.synthesize(_state())
        with pytest.raises(OutcomeNotFoundError):
            await service.get_outcome(InvestigationId("inv-1"))

    asyncio.run(scenario())


def test_blank_recommendation_raises() -> None:
    async def scenario() -> None:
        service = await _service_with_confirmed()
        engine, _ = _engine(
            service, '{"recommendation": "   ", "confidence": 0.5}'
        )

        with pytest.raises(DecisionEngineError):
            await engine.synthesize(_state())

    asyncio.run(scenario())
