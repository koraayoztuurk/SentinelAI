"""Tests for the Graph Analysis Agent, Flow and runner enrichment (ES-057).

The agent transforms a scripted analysis response into the typed
``GraphAnalysis`` (unknown observation kinds ignored, entity references
outside the snapshot discarded from provenance, malformed responses raised).
The flow assembles the finding-seeded neighbourhood, skips quietly when
there is none, and traces a produced analysis. The runner appends the
observations to the planner-visible knowledge with contained failure.
In-memory doubles, plain functions, ``asyncio.run``.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.ai.agents.graph_analysis import (
    EntitySnapshot,
    GraphAnalysis,
    GraphAnalysisAgent,
    GraphContext,
    GraphObservation,
    GraphObservationKind,
    RelationshipSnapshot,
)
from app.ai.errors import GraphAnalysisError
from app.ai.orchestration.assembler import InvestigationStateAssembler
from app.ai.orchestration.graph_analysis import GraphAnalysisFlow
from app.ai.orchestration.runner import InvestigationRunner
from app.domain.identifiers import (
    EntityId,
    InvestigationId,
    RelationshipId,
)
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import Confidence
from tests.support.builders import (
    build_entity,
    build_evidence,
    build_finding,
    build_investigation,
    build_relationship,
    make_graph_service,
    make_investigation_service,
)


class ScriptedLLM:
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
        return f"g-{self._count}"


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 15, tzinfo=UTC)


class RecordingTrace:
    def __init__(self) -> None:
        self.entries: list[TraceEntry] = []

    async def record_trace(self, entry: TraceEntry) -> TraceEntry:
        self.entries.append(entry)
        return entry


def _context() -> GraphContext:
    return GraphContext(
        investigation_id=InvestigationId("inv-1"),
        objectives=("Investigate: beaconing",),
        entities=(
            EntitySnapshot(
                id=EntityId("host-1"),
                type="endpoint",
                display_name="HOST-1",
                confidence=Confidence(0.95),
            ),
            EntitySnapshot(
                id=EntityId("ip-1"),
                type="ip",
                display_name="203.0.113.7",
                confidence=Confidence(0.9),
            ),
        ),
        relationships=(
            RelationshipSnapshot(
                id=RelationshipId("rel-1"),
                source_entity_id=EntityId("host-1"),
                target_entity_id=EntityId("ip-1"),
                type="communicates_with",
                confidence=Confidence(0.9),
            ),
        ),
    )


_GOOD_RESPONSE = (
    '{"summary": "A single egress chain.", "observations": ['
    '{"kind": "attack_path", "entities": ["host-1", "ip-1"], '
    '"detail": "HOST-1 egresses to a single external IP."}, '
    '{"kind": "made_up", "entities": [], "detail": "x"}, '
    '{"kind": "correlation", "entities": ["ghost"], '
    '"detail": "Shared infrastructure suspected."}]}'
)


def test_analysis_is_typed_filtered_and_attributed() -> None:
    async def scenario() -> None:
        agent = GraphAnalysisAgent(ScriptedLLM(_GOOD_RESPONSE))

        analysis = await agent.analyze(_context())

        assert analysis.summary == "A single egress chain."
        assert len(analysis.observations) == 2
        first, second = analysis.observations
        assert first.kind is GraphObservationKind.ATTACK_PATH
        assert [e.value for e in first.entities] == ["host-1", "ip-1"]
        # Unknown entity references lose the invented provenance only.
        assert second.kind is GraphObservationKind.CORRELATION
        assert second.entities == ()

    asyncio.run(scenario())


def test_reasoning_consumes_the_assembled_neighbourhood() -> None:
    async def scenario() -> None:
        llm = ScriptedLLM('{"summary": "ok", "observations": []}')
        await GraphAnalysisAgent(llm).analyze(_context())

        prompt = llm.prompts[0]
        assert "host-1" in prompt
        assert "communicates_with" in prompt
        assert "Investigate: beaconing" in prompt

    asyncio.run(scenario())


def test_malformed_response_raises() -> None:
    async def scenario() -> None:
        agent = GraphAnalysisAgent(ScriptedLLM("not json"))
        with pytest.raises(GraphAnalysisError):
            await agent.analyze(_context())

    asyncio.run(scenario())


def test_context_without_entities_is_a_precondition_violation() -> None:
    with pytest.raises(GraphAnalysisError):
        GraphContext(
            investigation_id=InvestigationId("inv-1"),
            objectives=("o",),
            entities=(),
            relationships=(),
        )


# ------------------------------------------------------- assembler + flow


async def _seeded_services():  # noqa: ANN202 - test helper tuple
    investigations = make_investigation_service()
    await investigations.create(
        build_investigation("inv-1", title="Beaconing")
    )
    await investigations.attach_evidence(build_evidence("ev-1", "inv-1"))
    await investigations.create_finding(
        build_finding(
            "f-1",
            "inv-1",
            supporting_evidence=("ev-1",),
            related_entities=("host-1",),
        )
    )
    graph = make_graph_service()
    await graph.create_entity(build_entity("host-1", display_name="HOST-1"))
    await graph.create_entity(
        build_entity("ip-1", type_value="ip", display_name="203.0.113.7")
    )
    await graph.create_relationship(
        build_relationship("rel-1", "host-1", "ip-1")
    )
    return investigations, graph


def test_assembler_builds_the_finding_seeded_neighbourhood() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)

        context = await assembler.assemble_graph_context(
            InvestigationId("inv-1")
        )

        assert context is not None
        entity_ids = {entity.id.value for entity in context.entities}
        assert entity_ids == {"host-1", "ip-1"}
        assert [r.id.value for r in context.relationships] == ["rel-1"]

    asyncio.run(scenario())


def test_assembler_returns_none_without_seeds_or_graph() -> None:
    async def scenario() -> None:
        investigations = make_investigation_service()
        await investigations.create(build_investigation("inv-1"))
        # No graph service composed at all.
        assert (
            await InvestigationStateAssembler(
                investigations
            ).assemble_graph_context(InvestigationId("inv-1"))
            is None
        )
        # Graph composed, but no finding names an entity.
        assert (
            await InvestigationStateAssembler(
                investigations, make_graph_service()
            ).assemble_graph_context(InvestigationId("inv-1"))
            is None
        )

    asyncio.run(scenario())


def test_flow_analyzes_and_traces() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        trace = RecordingTrace()
        flow = GraphAnalysisFlow(
            GraphAnalysisAgent(ScriptedLLM(_GOOD_RESPONSE)),
            assembler,
            SequentialIds(),
            FixedClock(),
            trace,
        )

        analysis = await flow.analyze(InvestigationId("inv-1"))

        assert analysis is not None
        assert len(trace.entries) == 1
        entry = trace.entries[0]
        assert entry.kind is TraceEntryKind.GRAPH_ANALYSIS
        assert entry.actor.value == "graph-analysis-agent"
        assert "2 observation(s)" in entry.summary
        assert "A single egress chain." in entry.summary

    asyncio.run(scenario())


def test_flow_skips_quietly_without_a_neighbourhood() -> None:
    async def scenario() -> None:
        investigations = make_investigation_service()
        await investigations.create(build_investigation("inv-1"))
        flow = GraphAnalysisFlow(
            GraphAnalysisAgent(ScriptedLLM("irrelevant")),
            InvestigationStateAssembler(investigations, make_graph_service()),
            SequentialIds(),
            FixedClock(),
            RecordingTrace(),
        )

        assert await flow.analyze(InvestigationId("inv-1")) is None

    asyncio.run(scenario())


# ---------------------------------------------------------- runner enrichment


class RecordingLoop:
    def __init__(self) -> None:
        self.states = []

    async def run(self, state):  # noqa: ANN001, ANN201 - protocol duck
        self.states.append(state)
        return "outcome"


class ScriptedGraphAnalysisFlow:
    def __init__(
        self,
        analysis: GraphAnalysis | None = None,
        error: Exception | None = None,
    ) -> None:
        self._analysis = analysis
        self._error = error

    async def analyze(
        self, investigation_id: InvestigationId
    ) -> GraphAnalysis | None:
        if self._error is not None:
            raise self._error
        return self._analysis


def test_runner_appends_observations_to_the_knowledge() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        loop = RecordingLoop()
        analysis = GraphAnalysis(
            investigation_id=InvestigationId("inv-1"),
            observations=(
                GraphObservation(
                    kind=GraphObservationKind.ATTACK_PATH,
                    detail="HOST-1 egresses to one external IP.",
                    entities=(EntityId("host-1"), EntityId("ip-1")),
                ),
            ),
            summary="chain",
        )
        runner = InvestigationRunner(
            assembler,
            loop,  # type: ignore[arg-type]
            graph_analysis=ScriptedGraphAnalysisFlow(analysis),  # type: ignore[arg-type]
        )

        await runner.run(InvestigationId("inv-1"))

        knowledge = loop.states[0].knowledge
        assert len(knowledge) == 1
        assert knowledge[0] == (
            "[graph-analysis] attack_path (entities: host-1,ip-1) "
            "HOST-1 egresses to one external IP."
        )

    asyncio.run(scenario())


def test_runner_contains_a_failed_graph_analysis() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        loop = RecordingLoop()
        runner = InvestigationRunner(
            assembler,
            loop,  # type: ignore[arg-type]
            graph_analysis=ScriptedGraphAnalysisFlow(  # type: ignore[arg-type]
                error=GraphAnalysisError("malformed analysis")
            ),
        )

        await runner.run(InvestigationId("inv-1"))

        assert loop.states[0].knowledge == ()

    asyncio.run(scenario())
