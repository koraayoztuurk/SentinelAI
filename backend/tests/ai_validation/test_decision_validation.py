"""Behavioral validation of the Decision Engine (ES-055, ai-validation).

The engine synthesizes, never fabricates: every adversarial provider response
raises rather than persisting a partial outcome; the reasoning input
demonstrably derives from the confirmed findings and the assembled state;
equivalent inputs yield an equivalent synthesis.
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
from app.domain.enums import FindingStatus
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence
from tests.ai_validation.support import (
    ADVERSARIAL_RESPONSES,
    RecordingLLM,
    ScriptedLLM,
)
from tests.support.builders import (
    build_evidence,
    build_finding,
    build_investigation,
    make_investigation_service,
)

pytestmark = pytest.mark.ai


class _SequentialIds:
    def __init__(self) -> None:
        self._count = 0

    def new_id(self) -> str:
        self._count += 1
        return f"out-{self._count}"


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 15, tzinfo=UTC)


def _state() -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId("inv-9"),
        status="created",
        confidence=Confidence(0.7),
        objectives=("Investigate: beaconing",),
    )


async def _confirmed_service() -> InvestigationService:
    service = make_investigation_service()
    await service.create(build_investigation("inv-9"))
    await service.attach_evidence(build_evidence("ev-1", "inv-9"))
    await service.create_finding(
        build_finding(
            "f-1",
            "inv-9",
            supporting_evidence=("ev-1",),
            status=FindingStatus.VALIDATED,
        )
    )
    return service


def test_adversarial_responses_never_fabricate_an_outcome() -> None:
    async def scenario() -> None:
        for response in ADVERSARIAL_RESPONSES:
            service = await _confirmed_service()
            engine = DecisionEngine(
                ScriptedLLM(response),
                service,
                _SequentialIds(),
                _FixedClock(),
            )
            with pytest.raises(DecisionEngineError):
                await engine.synthesize(_state())
            # Nothing was persisted for any degenerate synthesis.
            with pytest.raises(OutcomeNotFoundError):
                await service.get_outcome(InvestigationId("inv-9"))

    asyncio.run(scenario())


def test_reasoning_consumes_findings_and_state() -> None:
    async def scenario() -> None:
        service = await _confirmed_service()
        llm = RecordingLLM(
            '{"recommendation": "r", "confidence": 0.5}'
        )
        engine = DecisionEngine(
            llm, service, _SequentialIds(), _FixedClock()
        )

        await engine.synthesize(_state())

        prompt = llm.requests[0].prompt
        assert "inv-9" in prompt
        assert "f-1" in prompt
        assert "Investigate: beaconing" in prompt

    asyncio.run(scenario())


def test_equivalent_inputs_yield_an_equivalent_synthesis() -> None:
    async def scenario() -> None:
        response = (
            '{"recommendation": "Contain the host.", "confidence": 0.75, '
            '"detected_conflicts": ["dns timing"], "open_questions": []}'
        )
        outcomes = []
        for _ in range(2):
            service = await _confirmed_service()
            engine = DecisionEngine(
                ScriptedLLM(response),
                service,
                _SequentialIds(),
                _FixedClock(),
            )
            outcome = await engine.synthesize(_state())
            assert outcome is not None
            outcomes.append(outcome)

        first, second = outcomes
        assert first.recommendation == second.recommendation
        assert first.confidence == second.confidence
        assert first.detected_conflicts == second.detected_conflicts
        assert first.contributing_findings == second.contributing_findings

    asyncio.run(scenario())
