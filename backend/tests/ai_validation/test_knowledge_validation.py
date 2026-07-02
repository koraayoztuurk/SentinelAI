"""Knowledge Validation (ES-035, ai-validation §5).

Verifies the RAG pipeline's knowledge-utilization behavior: the assembled
context is invariant to retrieval order (knowledge consistency), every knowledge
item remains traceable in the built prompt (explainable validation / provenance),
insufficient context never yields a prompt (validation gate) and pipeline runs
over equal inputs are repeatable (behavioral consistency).
"""

import asyncio

import pytest

from app.ai import (
    InsufficientContextError,
    InvestigationState,
    RagPipeline,
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalStrategy,
    RetrievedItem,
    RetrievedKnowledge,
)
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence
from tests.ai_validation.support import make_state

pytestmark = pytest.mark.ai

_PLAN = RetrievalPlan(
    plan_id=RetrievalPlanId("p-1"),
    investigation_id=InvestigationId("inv-1"),
    strategies=(RetrievalStrategy.SEMANTIC, RetrievalStrategy.GRAPH),
)


class _FixedRetriever:
    """Retriever double returning a fixed knowledge set."""

    def __init__(self, *items: RetrievedItem) -> None:
        self._items = items

    async def retrieve(
        self, state: InvestigationState, plan: RetrievalPlan
    ) -> RetrievedKnowledge:
        return RetrievedKnowledge(plan_id=plan.plan_id, items=self._items)


def _item(
    strategy: RetrievalStrategy, reference: str, content: str
) -> RetrievedItem:
    return RetrievedItem(
        strategy=strategy,
        source=strategy.value,
        reference=reference,
        content=content,
        confidence=Confidence(0.7),
    )


_SEMANTIC = _item(RetrievalStrategy.SEMANTIC, "m-1", "similar incident found")
_GRAPH = _item(RetrievalStrategy.GRAPH, "e-1", "entity linked to campaign")


def test_context_is_invariant_to_retrieval_order() -> None:
    """Retrieval order never changes the assembled context or its prompt."""

    async def scenario() -> None:
        forward = await RagPipeline(_FixedRetriever(_SEMANTIC, _GRAPH)).run(
            make_state(), _PLAN
        )
        backward = await RagPipeline(_FixedRetriever(_GRAPH, _SEMANTIC)).run(
            make_state(), _PLAN
        )
        assert forward.context == backward.context
        assert forward.prompt == backward.prompt

    asyncio.run(scenario())


def test_prompt_preserves_provenance_for_every_item() -> None:
    """Each knowledge item stays traceable in the prompt (explainability)."""

    async def scenario() -> None:
        result = await RagPipeline(_FixedRetriever(_SEMANTIC, _GRAPH)).run(
            make_state(), _PLAN
        )
        for item in (_SEMANTIC, _GRAPH):
            assert item.strategy.value in result.prompt.text
            assert item.reference in result.prompt.text
            assert item.content in result.prompt.text

    asyncio.run(scenario())


def test_no_prompt_is_built_over_insufficient_context() -> None:
    """The validation gate refuses empty knowledge and missing objectives."""

    async def scenario() -> None:
        with pytest.raises(InsufficientContextError):
            await RagPipeline(_FixedRetriever()).run(make_state(), _PLAN)

        no_objectives = make_state(objectives=())
        with pytest.raises(InsufficientContextError):
            await RagPipeline(_FixedRetriever(_SEMANTIC)).run(no_objectives, _PLAN)

    asyncio.run(scenario())


def test_pipeline_runs_are_repeatable() -> None:
    """Equal inputs produce equal results across pipeline instances."""

    async def scenario() -> None:
        first = await RagPipeline(_FixedRetriever(_SEMANTIC, _GRAPH)).run(
            make_state(), _PLAN
        )
        second = await RagPipeline(_FixedRetriever(_SEMANTIC, _GRAPH)).run(
            make_state(), _PLAN
        )
        assert first == second

    asyncio.run(scenario())
