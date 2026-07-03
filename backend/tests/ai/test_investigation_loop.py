"""Unit tests for the Investigation Loop (ES-037, ADR-010/013).

Plain pytest functions. The loop is composed from the real Planner Agent over a
scripted fake LLM, an in-memory action executor, an in-memory state assembler,
an in-memory trace sink and deterministic id/clock sources. No live AI calls,
no live services.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.ai import (
    InvestigationLoop,
    InvestigationLoopError,
    InvestigationState,
    LLMRequest,
    LLMResponse,
    LoopEnd,
    PlannerAgent,
)
from app.application.planner.actions import (
    ControlAction,
    ControlKind,
    ExecutionError,
    ExecutionResult,
    ExecutionStatus,
    GetInvestigationAction,
    PlannerAction,
    TargetService,
)
from app.domain.identifiers import InvestigationId
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import Confidence

_GET = '{"action": "get_investigation"}'
_COMPLETE = '{"action": "control", "control": "complete"}'
_ESCALATE = '{"action": "control", "control": "escalate"}'
_NOW = datetime(2026, 1, 1, tzinfo=UTC)


class _ScriptedLLM:
    """Returns one canned response per call, repeating the last one afterwards."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self._calls = 0

    async def generate(self, request: LLMRequest) -> LLMResponse:
        index = min(self._calls, len(self._responses) - 1)
        self._calls += 1
        return LLMResponse(text=self._responses[index])


class _BrokenLLM:
    """Simulates a provider outage (ADR-013 resilience scenarios)."""

    async def generate(self, request: LLMRequest) -> LLMResponse:
        from app.ai.errors import LLMProviderError

        raise LLMProviderError("provider unavailable")


class _FakeExecutor:
    """Records executed actions and returns canned execution results."""

    def __init__(self, *failed_action_ids: str) -> None:
        self.executed: list[PlannerAction] = []
        self._failed = set(failed_action_ids)

    async def execute(self, action: PlannerAction) -> ExecutionResult:
        self.executed.append(action)
        if isinstance(action, ControlAction):
            return ExecutionResult(
                action_id=action.action_id,
                target=None,
                status=ExecutionStatus.COMPLETED,
                value=action.kind,
            )
        if action.action_id in self._failed:
            return ExecutionResult(
                action_id=action.action_id,
                target=TargetService.INVESTIGATION,
                status=ExecutionStatus.FAILED,
                error=ExecutionError(code="test.failure", message="failed"),
            )
        return ExecutionResult(
            action_id=action.action_id,
            target=TargetService.INVESTIGATION,
            status=ExecutionStatus.COMPLETED,
            value="ok",
        )


class _RecordingAssembler:
    """Appends each observed result to the state history (in-memory double)."""

    def __init__(self) -> None:
        self.observed: list[ExecutionResult] = []

    async def next_state(
        self, state: InvestigationState, result: ExecutionResult
    ) -> InvestigationState:
        self.observed.append(result)
        return InvestigationState(
            investigation_id=state.investigation_id,
            status=state.status,
            confidence=state.confidence,
            objectives=state.objectives,
            history=(*state.history, result.status.value),
        )


class _Ids:
    def __init__(self) -> None:
        self._count = 0

    def new_id(self) -> str:
        self._count += 1
        return f"a-{self._count}"


class _FixedClock:
    def now(self) -> datetime:
        return _NOW


class _RecordingTrace:
    """In-memory TraceSink double; optionally fails to prove best-effort."""

    def __init__(self, failing: bool = False) -> None:
        self.entries: list[TraceEntry] = []
        self._failing = failing

    async def record_trace(self, entry: TraceEntry) -> TraceEntry:
        if self._failing:
            raise RuntimeError("trace sink down")
        self.entries.append(entry)
        return entry


def _state(objectives: tuple[str, ...] = ("objective",)) -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId("inv-1"),
        status="active",
        confidence=Confidence(0.4),
        objectives=objectives,
    )


def _loop(
    llm: object,
    executor: _FakeExecutor,
    assembler: _RecordingAssembler,
    trace: _RecordingTrace | None = None,
    max_cycles: int = 5,
) -> InvestigationLoop:
    return InvestigationLoop(
        agent=PlannerAgent(llm),  # type: ignore[arg-type]
        executor=executor,
        assembler=assembler,
        ids=_Ids(),
        clock=_FixedClock(),
        trace=trace if trace is not None else _RecordingTrace(),
        max_cycles=max_cycles,
    )


def test_loop_completes_on_complete_control_action() -> None:
    executor = _FakeExecutor()
    loop = _loop(_ScriptedLLM(_GET, _COMPLETE), executor, _RecordingAssembler())

    outcome = asyncio.run(loop.run(_state()))

    assert outcome.end is LoopEnd.COMPLETED
    assert outcome.cycles == 2
    assert outcome.failure_code is None
    assert len(outcome.results) == 2
    # Ids interleave with trace-entry ids; the action ids are those the agent saw.
    get_action = executor.executed[0]
    control_action = executor.executed[1]
    assert isinstance(get_action, GetInvestigationAction)
    assert isinstance(control_action, ControlAction)
    assert control_action.kind is ControlKind.COMPLETE


def test_loop_escalates_on_escalate_control_action() -> None:
    executor = _FakeExecutor()
    loop = _loop(_ScriptedLLM(_ESCALATE), executor, _RecordingAssembler())

    outcome = asyncio.run(loop.run(_state()))

    assert outcome.end is LoopEnd.ESCALATED
    assert outcome.cycles == 1
    assert outcome.failure_code is None


def test_control_actions_are_executed_through_the_executor() -> None:
    executor = _FakeExecutor()
    loop = _loop(_ScriptedLLM(_COMPLETE), executor, _RecordingAssembler())

    outcome = asyncio.run(loop.run(_state()))

    assert outcome.results[-1].value is ControlKind.COMPLETE
    assert outcome.results[-1].status is ExecutionStatus.COMPLETED


def test_loop_exhausts_cycle_budget_without_control_action() -> None:
    executor = _FakeExecutor()
    assembler = _RecordingAssembler()
    loop = _loop(_ScriptedLLM(_GET), executor, assembler, max_cycles=3)

    outcome = asyncio.run(loop.run(_state()))

    assert outcome.end is LoopEnd.EXHAUSTED
    assert outcome.cycles == 3
    assert len(outcome.results) == 3
    assert assembler.observed == list(outcome.results)


def test_failed_execution_is_observed_and_agent_decides_next() -> None:
    executor = _FakeExecutor("a-1")
    assembler = _RecordingAssembler()
    loop = _loop(_ScriptedLLM(_GET, _ESCALATE), executor, assembler)

    outcome = asyncio.run(loop.run(_state()))

    assert outcome.end is LoopEnd.ESCALATED
    assert outcome.results[0].status is ExecutionStatus.FAILED
    assert assembler.observed[0].status is ExecutionStatus.FAILED


def test_provider_failure_degrades_to_escalation() -> None:
    # ADR-013: a provider outage never crashes the loop — it escalates with a
    # stable failure code and the investigation state stays intact.
    executor = _FakeExecutor()
    loop = _loop(_BrokenLLM(), executor, _RecordingAssembler())

    outcome = asyncio.run(loop.run(_state()))

    assert outcome.end is LoopEnd.ESCALATED
    assert outcome.failure_code == "ai.llm_provider_error"
    assert outcome.results == ()
    assert executor.executed == []


def test_precondition_violation_degrades_to_escalation() -> None:
    # An invalid state (no objectives) is contained the same way (ADR-013).
    loop = _loop(_ScriptedLLM(_COMPLETE), _FakeExecutor(), _RecordingAssembler())

    outcome = asyncio.run(loop.run(_state(objectives=())))

    assert outcome.end is LoopEnd.ESCALATED
    assert outcome.failure_code == "ai.planner_agent_error"


def test_loop_records_decisions_executions_and_outcome_in_trace() -> None:
    trace = _RecordingTrace()
    loop = _loop(
        _ScriptedLLM(_GET, _COMPLETE), _FakeExecutor(), _RecordingAssembler(), trace
    )

    asyncio.run(loop.run(_state()))

    kinds = [entry.kind for entry in trace.entries]
    assert kinds == [
        TraceEntryKind.PLANNER_DECISION,
        TraceEntryKind.ACTION_EXECUTION,
        TraceEntryKind.PLANNER_DECISION,
        TraceEntryKind.ACTION_EXECUTION,
        TraceEntryKind.LOOP_OUTCOME,
    ]
    assert all(
        entry.investigation_id == InvestigationId("inv-1")
        for entry in trace.entries
    )
    assert trace.entries[-1].summary == "completed after 2 cycle(s)"


def test_trace_failures_never_break_the_loop() -> None:
    # Best-effort tracing: a broken sink is contained; the loop still completes.
    loop = _loop(
        _ScriptedLLM(_COMPLETE),
        _FakeExecutor(),
        _RecordingAssembler(),
        _RecordingTrace(failing=True),
    )

    outcome = asyncio.run(loop.run(_state()))

    assert outcome.end is LoopEnd.COMPLETED


def test_non_positive_cycle_budget_is_rejected() -> None:
    with pytest.raises(InvestigationLoopError):
        InvestigationLoop(
            agent=PlannerAgent(_ScriptedLLM(_COMPLETE)),  # type: ignore[arg-type]
            executor=_FakeExecutor(),
            assembler=_RecordingAssembler(),
            ids=_Ids(),
            clock=_FixedClock(),
            trace=_RecordingTrace(),
            max_cycles=0,
        )
