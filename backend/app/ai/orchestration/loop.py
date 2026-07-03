"""Investigation Loop.

The AI Runtime composition that owns the Planner decision loop (ADR-010): the
Planner Agent selects exactly one Planner Action, the action executor (the
Planner Service in production) executes it, the next Investigation State is
assembled outside the loop through the ``StateAssembler`` port, and the cycle
repeats until the agent issues a control action (complete / escalate) or the
cycle budget is exhausted.

The agent runs through the **Agent Runtime** — the single execution path
(ADR-013). A failed agent execution (provider outage, timeout, precondition
violation) never propagates: the loop degrades to an **ESCALATED** outcome
carrying the stable failure code, and the investigation remains intact for the
analyst.

Every decision, execution and outcome is recorded into the Investigation Trace
through the best-effort ``TraceSink`` (explainability journal, domain-model
§11b). The loop is stateless and owns no data: identifiers and timestamps are
caller-supplied through the ``IdSource``/``Clock`` ports, and state assembly
remains the Investigation Workspace / Context Builder responsibility
(planner-agent §4).
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.ai.agents.planner.agent import PlannerAgent, PlannerDecisionRequest
from app.ai.agents.planner.state import InvestigationState
from app.ai.agents.runtime import AgentRuntime
from app.ai.errors import InvestigationLoopError
from app.ai.orchestration.tracing import (
    Clock,
    IdSource,
    TraceSink,
    record_best_effort,
)
from app.application.planner.actions import (
    ControlAction,
    ControlKind,
    ExecutionResult,
    PlannerAction,
)
from app.domain.identifiers import TraceEntryId
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import ActorRef

logger = logging.getLogger(__name__)

# Backwards-compatible alias: the loop's id port is the shared IdSource.
ActionIdSource = IdSource

_LOOP_ACTOR = ActorRef("investigation-loop")
_PLANNER_ACTOR = ActorRef("planner-agent")
_EXECUTOR_ACTOR = ActorRef("planner-service")


class ActionExecutor(Protocol):
    """Executes one Planner Action and returns its execution result.

    The production implementation is the Planner Service — the single, validated
    execution boundary over the backend services (ADR-010). The port exists so
    the loop composes against the documented seam rather than a concrete class.
    """

    async def execute(self, action: PlannerAction) -> ExecutionResult: ...


class StateAssembler(Protocol):
    """Assembles the next Investigation State after an executed action.

    Concrete assembly belongs to the Investigation Workspace / Context Builder
    (planner-agent §4); the loop never assembles state itself.
    """

    async def next_state(
        self, state: InvestigationState, result: ExecutionResult
    ) -> InvestigationState: ...


class LoopEnd(Enum):
    """How an Investigation Loop run ended."""

    COMPLETED = "completed"
    ESCALATED = "escalated"
    EXHAUSTED = "exhausted"


@dataclass(frozen=True, slots=True)
class LoopOutcome:
    """The observable outcome of one Investigation Loop run.

    ``results`` preserves every executed action's execution result in cycle
    order, keeping the run reproducible and explainable. ``failure_code`` carries
    the stable error code when the run escalated because an agent execution
    failed (ADR-013 degrade-to-escalation); it is ``None`` otherwise.
    """

    end: LoopEnd
    cycles: int
    results: tuple[ExecutionResult, ...]
    failure_code: str | None = None


class InvestigationLoop:
    """Runs the Planner decision loop over an assembled state (stateless)."""

    def __init__(
        self,
        agent: PlannerAgent,
        executor: ActionExecutor,
        assembler: StateAssembler,
        ids: IdSource,
        clock: Clock,
        trace: TraceSink,
        max_cycles: int,
    ) -> None:
        if max_cycles < 1:
            raise InvestigationLoopError("max_cycles must be positive.")
        self._agent = agent
        self._executor = executor
        self._assembler = assembler
        self._ids = ids
        self._clock = clock
        self._trace = trace
        self._max_cycles = max_cycles
        # The runtime is stateless and dependency-free; the loop owns one
        # (mirroring how the RAG pipeline owns its context-engineering parts).
        self._runtime = AgentRuntime()

    async def run(self, state: InvestigationState) -> LoopOutcome:
        """Run decide → execute → observe cycles until control or budget end."""

        results: list[ExecutionResult] = []
        for cycle in range(1, self._max_cycles + 1):
            action_id = self._ids.new_id()
            decision = await self._runtime.run(
                self._agent, PlannerDecisionRequest(state=state, action_id=action_id)
            )
            if decision.product is None:
                # Degrade-to-escalation (ADR-013): a failed agent execution ends
                # the run observably; it never crashes the investigation.
                failure_code = decision.error or "unknown_failure"
                await self._record(
                    state,
                    TraceEntryKind.LOOP_OUTCOME,
                    _LOOP_ACTOR,
                    f"escalated: agent execution failed ({failure_code})",
                    action_id,
                )
                logger.info(
                    "investigation loop escalated on agent failure "
                    "investigation_id=%s code=%s cycles=%s",
                    state.investigation_id.value,
                    failure_code,
                    cycle,
                )
                return LoopOutcome(
                    end=LoopEnd.ESCALATED,
                    cycles=cycle,
                    results=tuple(results),
                    failure_code=failure_code,
                )

            action = decision.product
            await self._record(
                state,
                TraceEntryKind.PLANNER_DECISION,
                _PLANNER_ACTOR,
                f"decided {type(action).__name__}",
                action_id,
            )

            result = await self._executor.execute(action)
            results.append(result)
            await self._record(
                state,
                TraceEntryKind.ACTION_EXECUTION,
                _EXECUTOR_ACTOR,
                f"executed {type(action).__name__}: {result.status.value}",
                action_id,
            )

            if isinstance(action, ControlAction):
                end = (
                    LoopEnd.COMPLETED
                    if action.kind is ControlKind.COMPLETE
                    else LoopEnd.ESCALATED
                )
                await self._record(
                    state,
                    TraceEntryKind.LOOP_OUTCOME,
                    _LOOP_ACTOR,
                    f"{end.value} after {cycle} cycle(s)",
                    action_id,
                )
                logger.info(
                    "investigation loop ended investigation_id=%s end=%s cycles=%s",
                    state.investigation_id.value,
                    end.value,
                    cycle,
                )
                return LoopOutcome(end=end, cycles=cycle, results=tuple(results))

            state = await self._assembler.next_state(state, result)

        await self._record(
            state,
            TraceEntryKind.LOOP_OUTCOME,
            _LOOP_ACTOR,
            f"exhausted after {self._max_cycles} cycle(s)",
            "budget",
        )
        logger.info(
            "investigation loop exhausted investigation_id=%s cycles=%s",
            state.investigation_id.value,
            self._max_cycles,
        )
        return LoopOutcome(
            end=LoopEnd.EXHAUSTED,
            cycles=self._max_cycles,
            results=tuple(results),
        )

    async def _record(
        self,
        state: InvestigationState,
        kind: TraceEntryKind,
        actor: ActorRef,
        summary: str,
        reference: str,
    ) -> None:
        entry = TraceEntry(
            id=TraceEntryId(self._ids.new_id()),
            investigation_id=state.investigation_id,
            kind=kind,
            actor=actor,
            summary=summary,
            reference=reference,
            created_at=self._clock.now(),
        )
        await record_best_effort(self._trace, entry)
