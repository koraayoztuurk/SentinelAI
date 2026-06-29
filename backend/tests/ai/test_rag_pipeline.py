"""Unit tests for the RAG Pipeline (ES-013).

Plain pytest functions with an in-memory Retriever double. No live AI calls, no
fixtures.
"""

import asyncio

import pytest

from app.ai import (
    ContextBuilder,
    ContextValidator,
    InsufficientContextError,
    InvestigationContext,
    InvestigationState,
    Prompt,
    PromptBuilder,
    RagPipeline,
    RagResult,
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalStrategy,
    RetrievedItem,
    RetrievedKnowledge,
    ValidationIssueCode,
)
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence

_PLAN_ID = RetrievalPlanId("p-1")


class _StubRetriever:
    def __init__(self, knowledge: RetrievedKnowledge) -> None:
        self._knowledge = knowledge

    async def retrieve(
        self, state: InvestigationState, plan: RetrievalPlan
    ) -> RetrievedKnowledge:
        return self._knowledge


def _state(
    objectives: tuple[str, ...] = ("determine malicious activity",),
) -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId("inv-1"),
        status="active",
        confidence=Confidence(0.4),
        objectives=objectives,
    )


def _plan() -> RetrievalPlan:
    return RetrievalPlan(
        plan_id=_PLAN_ID,
        investigation_id=InvestigationId("inv-1"),
        strategies=(RetrievalStrategy.STRUCTURED,),
    )


def _item(
    strategy: RetrievalStrategy,
    source: str,
    reference: str,
    content: str = "fact",
    confidence: float = 0.5,
) -> RetrievedItem:
    return RetrievedItem(
        strategy=strategy,
        source=source,
        reference=reference,
        content=content,
        confidence=Confidence(confidence),
    )


def _knowledge(*items: RetrievedItem) -> RetrievedKnowledge:
    return RetrievedKnowledge(plan_id=_PLAN_ID, items=items)


# ----------------------------------------------------------------- ContextBuilder


def test_context_builder_preserves_state_fields() -> None:
    context = ContextBuilder().build(
        _state(), _knowledge(_item(RetrievalStrategy.STRUCTURED, "memory", "m-1"))
    )
    assert context.investigation_id == InvestigationId("inv-1")
    assert context.objectives == ("determine malicious activity",)
    assert context.confidence == Confidence(0.4)


def test_context_builder_deduplicates_by_source_reference() -> None:
    item_a = _item(RetrievalStrategy.STRUCTURED, "memory", "m-1", content="first")
    item_dup = _item(RetrievalStrategy.STRUCTURED, "memory", "m-1", content="second")
    context = ContextBuilder().build(_state(), _knowledge(item_a, item_dup))
    assert context.knowledge == (item_a,)


def test_context_builder_orders_deterministically() -> None:
    # Provided out of canonical order: graph before semantic, references unsorted.
    graph_item = _item(RetrievalStrategy.GRAPH, "graph", "e-1")
    semantic_b = _item(RetrievalStrategy.SEMANTIC, "memory", "m-2")
    semantic_a = _item(RetrievalStrategy.SEMANTIC, "memory", "m-1")
    context = ContextBuilder().build(
        _state(), _knowledge(graph_item, semantic_b, semantic_a)
    )
    # Canonical: SEMANTIC before GRAPH; within source, reference ascending.
    assert context.knowledge == (semantic_a, semantic_b, graph_item)


# --------------------------------------------------------------- ContextValidator


def test_validator_accepts_populated_context() -> None:
    context = ContextBuilder().build(
        _state(), _knowledge(_item(RetrievalStrategy.STRUCTURED, "memory", "m-1"))
    )
    result = ContextValidator().validate(context)
    assert result.is_valid
    assert result.issues == ()


def test_validator_flags_empty_context() -> None:
    context = ContextBuilder().build(_state(), _knowledge())
    result = ContextValidator().validate(context)
    assert not result.is_valid
    assert [issue.code for issue in result.issues] == [
        ValidationIssueCode.EMPTY_CONTEXT
    ]


def test_validator_flags_missing_objectives() -> None:
    context = InvestigationContext(
        investigation_id=InvestigationId("inv-1"),
        objectives=(),
        confidence=Confidence(0.4),
        knowledge=(_item(RetrievalStrategy.STRUCTURED, "memory", "m-1"),),
    )
    result = ContextValidator().validate(context)
    assert not result.is_valid
    assert [issue.code for issue in result.issues] == [
        ValidationIssueCode.MISSING_OBJECTIVES
    ]


# ----------------------------------------------------------------- PromptBuilder


def test_prompt_builder_is_provider_neutral_and_includes_provenance() -> None:
    context = ContextBuilder().build(
        _state(), _knowledge(_item(RetrievalStrategy.STRUCTURED, "memory", "m-1"))
    )
    prompt = PromptBuilder().build(context)
    assert isinstance(prompt, Prompt)
    assert "determine malicious activity" in prompt.text
    assert "structured" in prompt.text
    assert "memory/m-1" in prompt.text


def test_prompt_builder_is_deterministic() -> None:
    context = ContextBuilder().build(
        _state(), _knowledge(_item(RetrievalStrategy.STRUCTURED, "memory", "m-1"))
    )
    assert PromptBuilder().build(context) == PromptBuilder().build(context)


# ------------------------------------------------------------------- RagPipeline


def test_pipeline_happy_path_returns_result() -> None:
    retriever = _StubRetriever(
        _knowledge(_item(RetrievalStrategy.STRUCTURED, "memory", "m-1"))
    )
    result = asyncio.run(RagPipeline(retriever).run(_state(), _plan()))
    assert isinstance(result, RagResult)
    assert result.context.knowledge != ()
    assert isinstance(result.prompt, Prompt)


def test_pipeline_raises_on_empty_retrieval() -> None:
    retriever = _StubRetriever(_knowledge())
    with pytest.raises(InsufficientContextError):
        asyncio.run(RagPipeline(retriever).run(_state(), _plan()))


def test_pipeline_is_deterministic() -> None:
    knowledge = _knowledge(
        _item(RetrievalStrategy.GRAPH, "graph", "e-1"),
        _item(RetrievalStrategy.SEMANTIC, "memory", "m-1"),
    )
    first = asyncio.run(RagPipeline(_StubRetriever(knowledge)).run(_state(), _plan()))
    second = asyncio.run(RagPipeline(_StubRetriever(knowledge)).run(_state(), _plan()))
    assert first == second
