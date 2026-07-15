"""Tests for the retrieval-enriched Investigation run entry point (ES-051).

The runner executes the Retrieval Flow once per run: retrieved knowledge is
attached to the initial state (and preserved across cycles by the assembler);
a failed or insufficient retrieval is contained — the run proceeds without
retrieved knowledge. Scripted doubles, plain functions, ``asyncio.run``.
"""

import asyncio

from app.ai.agents.memory.plan import RetrievalPlanId, RetrievalStrategy
from app.ai.agents.planner.state import InvestigationState
from app.ai.errors import InsufficientContextError, MemoryAgentError
from app.ai.orchestration.runner import InvestigationRunner
from app.ai.rag.context_builder import InvestigationContext
from app.ai.rag.pipeline import RagResult
from app.ai.rag.prompt_builder import Prompt
from app.ai.rag.retriever import RetrievedItem
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence


class RecordingAssembler:
    """Assembler double returning a fixed state."""

    def __init__(self, state: InvestigationState) -> None:
        self._state = state

    async def assemble(
        self, investigation_id: InvestigationId
    ) -> InvestigationState:
        return self._state


class RecordingLoop:
    """Loop double recording the state it was run with."""

    def __init__(self) -> None:
        self.states: list[InvestigationState] = []

    async def run(self, state: InvestigationState) -> str:
        self.states.append(state)
        return "outcome"


class ScriptedRetrievalFlow:
    """Retrieval Flow double: scripted result or scripted failure."""

    def __init__(
        self,
        result: RagResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.plan_ids: list[RetrievalPlanId] = []

    async def run(
        self, state: InvestigationState, plan_id: RetrievalPlanId
    ) -> RagResult:
        self.plan_ids.append(plan_id)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class SequentialIds:
    def __init__(self) -> None:
        self._count = 0

    def new_id(self) -> str:
        self._count += 1
        return f"id-{self._count}"


def _state() -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId("inv-1"),
        status="active",
        confidence=Confidence(0.5),
        objectives=("Investigate: test",),
    )


def _rag_result() -> RagResult:
    item = RetrievedItem(
        strategy=RetrievalStrategy.SEMANTIC,
        source="memory",
        reference="m-1",
        content="C2 beacon pattern",
        confidence=Confidence(0.87),
    )
    context = InvestigationContext(
        investigation_id=InvestigationId("inv-1"),
        objectives=("Investigate: test",),
        confidence=Confidence(0.5),
        knowledge=(item,),
    )
    return RagResult(context=context, prompt=Prompt(text="prompt"))


def test_run_attaches_retrieved_knowledge_to_the_initial_state() -> None:
    async def scenario() -> None:
        loop = RecordingLoop()
        flow = ScriptedRetrievalFlow(result=_rag_result())
        runner = InvestigationRunner(
            RecordingAssembler(_state()),  # type: ignore[arg-type]
            loop,  # type: ignore[arg-type]
            flow,  # type: ignore[arg-type]
            SequentialIds(),
        )

        await runner.run(InvestigationId("inv-1"))

        assert len(loop.states) == 1
        knowledge = loop.states[0].knowledge
        assert len(knowledge) == 1
        # Provenance-preserving line: strategy, source:reference, confidence.
        assert knowledge[0] == (
            "[semantic] memory:m-1 (confidence=0.87) C2 beacon pattern"
        )
        # The retrieval-plan id was caller-supplied through the IdSource.
        assert flow.plan_ids == [RetrievalPlanId("id-1")]

    asyncio.run(scenario())


def test_run_proceeds_without_knowledge_when_context_is_insufficient() -> None:
    async def scenario() -> None:
        loop = RecordingLoop()
        flow = ScriptedRetrievalFlow(
            error=InsufficientContextError("no knowledge")
        )
        runner = InvestigationRunner(
            RecordingAssembler(_state()),  # type: ignore[arg-type]
            loop,  # type: ignore[arg-type]
            flow,  # type: ignore[arg-type]
            SequentialIds(),
        )

        await runner.run(InvestigationId("inv-1"))

        assert loop.states[0].knowledge == ()

    asyncio.run(scenario())


def test_run_proceeds_without_knowledge_when_planning_fails() -> None:
    async def scenario() -> None:
        loop = RecordingLoop()
        flow = ScriptedRetrievalFlow(
            error=MemoryAgentError("provider outage")
        )
        runner = InvestigationRunner(
            RecordingAssembler(_state()),  # type: ignore[arg-type]
            loop,  # type: ignore[arg-type]
            flow,  # type: ignore[arg-type]
            SequentialIds(),
        )

        await runner.run(InvestigationId("inv-1"))

        assert loop.states[0].knowledge == ()

    asyncio.run(scenario())


def test_runner_without_retrieval_flow_is_unchanged() -> None:
    async def scenario() -> None:
        loop = RecordingLoop()
        runner = InvestigationRunner(
            RecordingAssembler(_state()),  # type: ignore[arg-type]
            loop,  # type: ignore[arg-type]
        )

        await runner.run(InvestigationId("inv-1"))

        assert loop.states[0].knowledge == ()

    asyncio.run(scenario())


def test_long_retrieved_content_is_bounded_in_the_knowledge_line() -> None:
    async def scenario() -> None:
        item = RetrievedItem(
            strategy=RetrievalStrategy.STRUCTURED,
            source="memory",
            reference="m-1",
            content="x" * 500,
            confidence=Confidence(0.5),
        )
        context = InvestigationContext(
            investigation_id=InvestigationId("inv-1"),
            objectives=("Investigate: test",),
            confidence=Confidence(0.5),
            knowledge=(item,),
        )
        loop = RecordingLoop()
        flow = ScriptedRetrievalFlow(
            result=RagResult(context=context, prompt=Prompt(text="p"))
        )
        runner = InvestigationRunner(
            RecordingAssembler(_state()),  # type: ignore[arg-type]
            loop,  # type: ignore[arg-type]
            flow,  # type: ignore[arg-type]
            SequentialIds(),
        )

        await runner.run(InvestigationId("inv-1"))

        line = loop.states[0].knowledge[0]
        # Content is truncated so retrieval cannot flood the planner prompt.
        assert len(line) < 400
        assert line.endswith("…")

    asyncio.run(scenario())
