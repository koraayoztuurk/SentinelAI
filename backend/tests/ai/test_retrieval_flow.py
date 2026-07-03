"""Unit tests for the Retrieval Flow (ES-037, ADR-010/013).

Plain pytest functions. The flow is composed from the real Memory Agent over a
fake LLM, the real RAG Pipeline over an in-memory Retriever, and in-memory
trace/id/clock doubles. No live AI calls, no live knowledge sources.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.ai import (
    InsufficientContextError,
    InvestigationState,
    LLMRequest,
    LLMResponse,
    MemoryAgent,
    MemoryAgentError,
    RagPipeline,
    RetrievalFlow,
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalStrategy,
    RetrievedItem,
    RetrievedKnowledge,
)
from app.domain.identifiers import InvestigationId
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import Confidence

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


class _FakeLLM:
    def __init__(self, response_text: str) -> None:
        self._text = response_text

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=self._text)


class _BrokenLLM:
    async def generate(self, request: LLMRequest) -> LLMResponse:
        from app.ai.errors import LLMProviderError

        raise LLMProviderError("provider unavailable")


class _InMemoryRetriever:
    """Returns one canned item per planned strategy and records the plan."""

    def __init__(self) -> None:
        self.plans: list[RetrievalPlan] = []

    async def retrieve(
        self, state: InvestigationState, plan: RetrievalPlan
    ) -> RetrievedKnowledge:
        self.plans.append(plan)
        items = tuple(
            RetrievedItem(
                strategy=strategy,
                source="memory",
                reference=f"ref-{strategy.value}",
                content=f"knowledge via {strategy.value}",
                confidence=Confidence(0.8),
            )
            for strategy in plan.strategies
        )
        return RetrievedKnowledge(plan_id=plan.plan_id, items=items)


class _Ids:
    def __init__(self) -> None:
        self._count = 0

    def new_id(self) -> str:
        self._count += 1
        return f"t-{self._count}"


class _FixedClock:
    def now(self) -> datetime:
        return _NOW


class _RecordingTrace:
    def __init__(self) -> None:
        self.entries: list[TraceEntry] = []

    async def record_trace(self, entry: TraceEntry) -> TraceEntry:
        self.entries.append(entry)
        return entry


def _state() -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId("inv-1"),
        status="active",
        confidence=Confidence(0.4),
        objectives=("determine whether malicious activity exists",),
    )


def _flow(
    llm: object,
) -> tuple[RetrievalFlow, _InMemoryRetriever, _RecordingTrace]:
    retriever = _InMemoryRetriever()
    trace = _RecordingTrace()
    flow = RetrievalFlow(
        agent=MemoryAgent(llm),  # type: ignore[arg-type]
        pipeline=RagPipeline(retriever),
        ids=_Ids(),
        clock=_FixedClock(),
        trace=trace,
    )
    return flow, retriever, trace


def test_flow_runs_agent_then_pipeline() -> None:
    flow, retriever, _ = _flow(_FakeLLM('{"strategies": ["semantic", "graph"]}'))

    result = asyncio.run(flow.run(_state(), RetrievalPlanId("plan-1")))

    assert retriever.plans == [
        RetrievalPlan(
            plan_id=RetrievalPlanId("plan-1"),
            investigation_id=InvestigationId("inv-1"),
            strategies=(RetrievalStrategy.SEMANTIC, RetrievalStrategy.GRAPH),
        )
    ]
    assert len(result.context.knowledge) == 2
    assert "knowledge via semantic" in result.prompt.text
    assert "knowledge via graph" in result.prompt.text


def test_flow_records_a_retrieval_trace_entry() -> None:
    flow, _, trace = _flow(_FakeLLM('{"strategies": ["semantic"]}'))

    asyncio.run(flow.run(_state(), RetrievalPlanId("plan-1")))

    assert len(trace.entries) == 1
    entry = trace.entries[0]
    assert entry.kind is TraceEntryKind.RETRIEVAL
    assert entry.reference == "plan-1"
    assert "semantic" in entry.summary


def test_flow_reports_insufficient_context_for_empty_selection() -> None:
    flow, _, _ = _flow(_FakeLLM('{"strategies": ["unknown"]}'))

    with pytest.raises(InsufficientContextError):
        asyncio.run(flow.run(_state(), RetrievalPlanId("plan-1")))


def test_provider_failure_is_contained_and_reported() -> None:
    # ADR-013: the agent runs through the runtime; a contained failure is
    # re-raised as MemoryAgentError carrying the stable code.
    flow, _, _ = _flow(_BrokenLLM())

    with pytest.raises(MemoryAgentError) as excinfo:
        asyncio.run(flow.run(_state(), RetrievalPlanId("plan-1")))

    assert "ai.llm_provider_error" in str(excinfo.value)
