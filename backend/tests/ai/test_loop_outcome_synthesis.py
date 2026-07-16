"""Tests for the Investigation Loop's outcome-synthesis step (ES-055).

A completed run triggers the synthesizer exactly once and traces the
synthesized outcome; an escalated run never synthesizes; a synthesis failure
is contained (the run still completes, the failure is traced); a loop without
a synthesizer behaves exactly as before. Scripted doubles, plain functions,
``asyncio.run``.
"""

import asyncio
from datetime import UTC, datetime

from app.ai.agents.planner.agent import PlannerAgent
from app.ai.agents.planner.state import InvestigationState
from app.ai.agents.validation import (
    ValidationAssessment,
    ValidationIssue,
    ValidationIssueKind,
)
from app.ai.errors import DecisionEngineError, ValidationAgentError
from app.ai.orchestration.loop import InvestigationLoop, LoopEnd
from app.application.planner.actions import (
    ExecutionResult,
    ExecutionStatus,
    PlannerAction,
)
from app.domain.enums import InvestigationOutcomeStatus
from app.domain.identifiers import (
    FindingId,
    InvestigationId,
    InvestigationOutcomeId,
)
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import Confidence


class ScriptedLLM:
    def __init__(self, text: str) -> None:
        self._text = text

    async def generate(self, request):  # noqa: ANN001, ANN201 - protocol duck
        class _Response:
            text = self._text

        return _Response()


class RecordingExecutor:
    async def execute(self, action: PlannerAction) -> ExecutionResult:
        return ExecutionResult(
            action_id=action.action_id,
            target=None,
            status=ExecutionStatus.COMPLETED,
            value=action,
        )


class StaticAssembler:
    def __init__(self, state: InvestigationState) -> None:
        self._state = state

    async def next_state(
        self, state: InvestigationState, result: ExecutionResult
    ) -> InvestigationState:
        return self._state


class RecordingTrace:
    def __init__(self) -> None:
        self.entries: list[TraceEntry] = []

    async def record_trace(self, entry: TraceEntry) -> TraceEntry:
        self.entries.append(entry)
        return entry


class SequentialIds:
    def __init__(self) -> None:
        self._count = 0

    def new_id(self) -> str:
        self._count += 1
        return f"id-{self._count}"


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 15, tzinfo=UTC)


class RecordingSynthesizer:
    """Synthesizer double: scripted outcome, error, or skip (None)."""

    def __init__(
        self,
        outcome: InvestigationOutcome | None = None,
        error: Exception | None = None,
    ) -> None:
        self._outcome = outcome
        self._error = error
        self.states: list[InvestigationState] = []
        self.assessments: list[object] = []

    async def synthesize(
        self,
        state: InvestigationState,
        assessment: object = None,
    ) -> InvestigationOutcome | None:
        self.states.append(state)
        self.assessments.append(assessment)
        if self._error is not None:
            raise self._error
        return self._outcome


def _state() -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId("inv-1"),
        status="created",
        confidence=Confidence(0.8),
        objectives=("Investigate: test",),
    )


def _outcome() -> InvestigationOutcome:
    return InvestigationOutcome(
        id=InvestigationOutcomeId("out-1"),
        investigation_id=InvestigationId("inv-1"),
        confidence=Confidence(0.9),
        recommendation="Contain the host.",
        status=InvestigationOutcomeStatus.SYNTHESIZED,
        created_at=datetime(2026, 7, 15, tzinfo=UTC),
        detected_conflicts=("a",),
        open_questions=(),
    )


class RecordingValidator:
    """Validator double: scripted assessment, error, or skip (None)."""

    def __init__(
        self,
        assessment: ValidationAssessment | None = None,
        error: Exception | None = None,
    ) -> None:
        self._assessment = assessment
        self._error = error
        self.investigations: list[InvestigationId] = []

    async def assess(
        self, investigation_id: InvestigationId
    ) -> ValidationAssessment | None:
        self.investigations.append(investigation_id)
        if self._error is not None:
            raise self._error
        return self._assessment


def _assessment() -> ValidationAssessment:
    return ValidationAssessment(
        investigation_id=InvestigationId("inv-1"),
        assessed_findings=(FindingId("f-1"),),
        issues=(
            ValidationIssue(
                kind=ValidationIssueKind.MISSING_EVIDENCE,
                detail="No corroboration.",
                finding_id=FindingId("f-1"),
            ),
        ),
        summary="One finding lacks corroboration.",
    )


def _loop(
    llm_text: str,
    trace: RecordingTrace,
    synthesizer: RecordingSynthesizer | None,
    validator: RecordingValidator | None = None,
) -> InvestigationLoop:
    state = _state()
    return InvestigationLoop(
        PlannerAgent(ScriptedLLM(llm_text)),
        RecordingExecutor(),
        StaticAssembler(state),
        SequentialIds(),
        FixedClock(),
        trace,
        max_cycles=3,
        synthesizer=synthesizer,
        validator=validator,
    )


_COMPLETE = '{"action": "control", "control": "complete"}'
_UNKNOWN = "not json"  # resolves to the escalate fallback


def test_completed_run_synthesizes_and_traces_the_outcome() -> None:
    async def scenario() -> None:
        trace = RecordingTrace()
        synthesizer = RecordingSynthesizer(outcome=_outcome())
        loop = _loop(_COMPLETE, trace, synthesizer)

        result = await loop.run(_state())

        assert result.end is LoopEnd.COMPLETED
        assert len(synthesizer.states) == 1
        kinds = [entry.kind for entry in trace.entries]
        assert TraceEntryKind.OUTCOME_SYNTHESIS in kinds
        synthesis = next(
            entry
            for entry in trace.entries
            if entry.kind is TraceEntryKind.OUTCOME_SYNTHESIS
        )
        assert synthesis.actor.value == "decision-engine"
        assert synthesis.reference == "out-1"
        assert "confidence=0.90" in synthesis.summary
        assert "1 conflict(s)" in synthesis.summary
        # Synthesis is traced before the terminal loop outcome.
        assert kinds.index(TraceEntryKind.OUTCOME_SYNTHESIS) < kinds.index(
            TraceEntryKind.LOOP_OUTCOME
        )

    asyncio.run(scenario())


def test_escalated_run_never_synthesizes() -> None:
    async def scenario() -> None:
        trace = RecordingTrace()
        synthesizer = RecordingSynthesizer(outcome=_outcome())
        loop = _loop(_UNKNOWN, trace, synthesizer)

        result = await loop.run(_state())

        assert result.end is LoopEnd.ESCALATED
        assert synthesizer.states == []
        kinds = [entry.kind for entry in trace.entries]
        assert TraceEntryKind.OUTCOME_SYNTHESIS not in kinds

    asyncio.run(scenario())


def test_synthesis_failure_is_contained_and_traced() -> None:
    async def scenario() -> None:
        trace = RecordingTrace()
        synthesizer = RecordingSynthesizer(
            error=DecisionEngineError("malformed synthesis")
        )
        loop = _loop(_COMPLETE, trace, synthesizer)

        result = await loop.run(_state())

        # The completed run is never broken by a failed synthesis.
        assert result.end is LoopEnd.COMPLETED
        synthesis = next(
            entry
            for entry in trace.entries
            if entry.kind is TraceEntryKind.OUTCOME_SYNTHESIS
        )
        assert "failed" in synthesis.summary
        assert "ai.decision_engine_error" in synthesis.summary

    asyncio.run(scenario())


def test_skipped_synthesis_leaves_no_trace_entry() -> None:
    async def scenario() -> None:
        trace = RecordingTrace()
        synthesizer = RecordingSynthesizer(outcome=None)
        loop = _loop(_COMPLETE, trace, synthesizer)

        result = await loop.run(_state())

        assert result.end is LoopEnd.COMPLETED
        assert len(synthesizer.states) == 1
        kinds = [entry.kind for entry in trace.entries]
        assert TraceEntryKind.OUTCOME_SYNTHESIS not in kinds

    asyncio.run(scenario())


def test_completed_run_validates_before_synthesis() -> None:
    async def scenario() -> None:
        trace = RecordingTrace()
        synthesizer = RecordingSynthesizer(outcome=_outcome())
        validator = RecordingValidator(assessment=_assessment())
        loop = _loop(_COMPLETE, trace, synthesizer, validator)

        result = await loop.run(_state())

        assert result.end is LoopEnd.COMPLETED
        assert validator.investigations == [InvestigationId("inv-1")]
        # The assessment reached the synthesizer (the documented input).
        assert synthesizer.assessments == [validator._assessment]
        kinds = [entry.kind for entry in trace.entries]
        assert TraceEntryKind.VALIDATION in kinds
        validation = next(
            entry
            for entry in trace.entries
            if entry.kind is TraceEntryKind.VALIDATION
        )
        assert validation.actor.value == "validation-agent"
        assert "1 issue(s)" in validation.summary
        assert "lacks corroboration" in validation.summary
        # Ordering: validation → synthesis → terminal loop outcome.
        assert kinds.index(TraceEntryKind.VALIDATION) < kinds.index(
            TraceEntryKind.OUTCOME_SYNTHESIS
        )

    asyncio.run(scenario())


def test_validation_failure_is_contained_and_synthesis_still_runs() -> None:
    async def scenario() -> None:
        trace = RecordingTrace()
        synthesizer = RecordingSynthesizer(outcome=_outcome())
        validator = RecordingValidator(
            error=ValidationAgentError("malformed assessment")
        )
        loop = _loop(_COMPLETE, trace, synthesizer, validator)

        result = await loop.run(_state())

        assert result.end is LoopEnd.COMPLETED
        # Synthesis proceeded without an assessment.
        assert synthesizer.assessments == [None]
        validation = next(
            entry
            for entry in trace.entries
            if entry.kind is TraceEntryKind.VALIDATION
        )
        assert "failed" in validation.summary
        assert "ai.validation_agent_error" in validation.summary

    asyncio.run(scenario())


def test_escalated_run_never_validates() -> None:
    async def scenario() -> None:
        trace = RecordingTrace()
        validator = RecordingValidator(assessment=_assessment())
        loop = _loop(_UNKNOWN, trace, RecordingSynthesizer(), validator)

        result = await loop.run(_state())

        assert result.end is LoopEnd.ESCALATED
        assert validator.investigations == []

    asyncio.run(scenario())


def test_loop_without_synthesizer_is_unchanged() -> None:
    async def scenario() -> None:
        trace = RecordingTrace()
        loop = _loop(_COMPLETE, trace, None)

        result = await loop.run(_state())

        assert result.end is LoopEnd.COMPLETED
        kinds = [entry.kind for entry in trace.entries]
        assert kinds == [
            TraceEntryKind.PLANNER_DECISION,
            TraceEntryKind.ACTION_EXECUTION,
            TraceEntryKind.LOOP_OUTCOME,
        ]

    asyncio.run(scenario())
