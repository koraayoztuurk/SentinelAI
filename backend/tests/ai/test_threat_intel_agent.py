"""Tests for the Threat Intelligence Agent, Flow and runner enrichment (ES-059).

The agent transforms a scripted correlation response into the typed
``ThreatIntelReport`` (unknown observation kinds ignored, references outside
the assembled intelligence discarded from provenance, malformed responses
raised). The flow derives focused queries from the seed, retrieves through
the external knowledge providers with per-provider containment, skips quietly
when nothing external applies, and traces a produced report. The runner
appends the observations to the planner-visible knowledge with contained
failure. In-memory doubles, plain functions, ``asyncio.run``.
"""

import asyncio
from datetime import UTC, datetime

import pytest

from app.ai.agents.threat_intel import (
    ThreatIntelAgent,
    ThreatIntelContext,
    ThreatIntelEntity,
    ThreatIntelObservation,
    ThreatIntelObservationKind,
    ThreatIntelReport,
)
from app.ai.errors import ExternalKnowledgeError, ThreatIntelAgentError
from app.ai.orchestration.assembler import InvestigationStateAssembler
from app.ai.orchestration.runner import InvestigationRunner
from app.ai.orchestration.threat_intel import ThreatIntelFlow
from app.ai.providers.external import (
    ExternalKnowledgeItem,
    ExternalKnowledgeQuery,
)
from app.domain.identifiers import EntityId, InvestigationId
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import Confidence
from tests.support.builders import (
    build_entity,
    build_evidence,
    build_finding,
    build_investigation,
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
        return f"t-{self._count}"


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 7, 17, tzinfo=UTC)


class RecordingTrace:
    def __init__(self) -> None:
        self.entries: list[TraceEntry] = []

    async def record_trace(self, entry: TraceEntry) -> TraceEntry:
        self.entries.append(entry)
        return entry


class ScriptedExternalProvider:
    """External provider double returning scripted items per lookup."""

    def __init__(self, items: tuple[ExternalKnowledgeItem, ...] = ()) -> None:
        self.queries: list[str] = []
        self._items = items

    async def lookup(
        self, query: ExternalKnowledgeQuery
    ) -> tuple[ExternalKnowledgeItem, ...]:
        self.queries.append(query.query)
        return self._items


class FailingExternalProvider:
    async def lookup(
        self, query: ExternalKnowledgeQuery
    ) -> tuple[ExternalKnowledgeItem, ...]:
        raise ExternalKnowledgeError("The external feed is unreachable.")


def _intel(reference: str, source: str = "mitre-attack") -> ExternalKnowledgeItem:
    return ExternalKnowledgeItem(
        source=source,
        reference=reference,
        content=f"{reference}: external knowledge content",
        confidence=Confidence(0.6),
    )


def _context() -> ThreatIntelContext:
    return ThreatIntelContext(
        investigation_id=InvestigationId("inv-1"),
        objectives=("Investigate: beaconing",),
        entities=(
            ThreatIntelEntity(
                id=EntityId("host-1"), type="endpoint", display_name="HOST-1"
            ),
        ),
        intelligence=(_intel("T1071"), _intel("CVE-2024-0001", source="nvd")),
    )


_GOOD_RESPONSE = (
    '{"summary": "Beaconing consistent with C2 over app-layer protocols.", '
    '"observations": ['
    '{"kind": "attack_mapping", "references": ["T1071"], '
    '"detail": "The periodic connections match T1071."}, '
    '{"kind": "made_up", "references": [], "detail": "x"}, '
    '{"kind": "cve_correlation", "references": ["CVE-9999-9999"], '
    '"detail": "A vulnerability may be involved."}]}'
)


# ----------------------------------------------------------------------- agent


def test_report_is_typed_filtered_and_attributed() -> None:
    async def scenario() -> None:
        agent = ThreatIntelAgent(ScriptedLLM(_GOOD_RESPONSE))

        report = await agent.correlate(_context())

        assert report.summary == (
            "Beaconing consistent with C2 over app-layer protocols."
        )
        assert len(report.observations) == 2
        first, second = report.observations
        assert first.kind is ThreatIntelObservationKind.ATTACK_MAPPING
        assert first.references == ("T1071",)
        # A reference the platform never retrieved loses the invented
        # provenance only; the observation itself survives.
        assert second.kind is ThreatIntelObservationKind.CVE_CORRELATION
        assert second.references == ()

    asyncio.run(scenario())


def test_reasoning_consumes_the_assembled_context() -> None:
    async def scenario() -> None:
        llm = ScriptedLLM('{"summary": "ok", "observations": []}')
        await ThreatIntelAgent(llm).correlate(_context())

        prompt = llm.prompts[0]
        assert "ref=T1071" in prompt
        assert "source=nvd" in prompt
        assert "HOST-1" in prompt
        assert "Investigate: beaconing" in prompt

    asyncio.run(scenario())


def test_malformed_response_raises() -> None:
    async def scenario() -> None:
        agent = ThreatIntelAgent(ScriptedLLM("not json"))
        with pytest.raises(ThreatIntelAgentError):
            await agent.correlate(_context())

    asyncio.run(scenario())


def test_summary_less_response_raises() -> None:
    async def scenario() -> None:
        agent = ThreatIntelAgent(ScriptedLLM('{"observations": []}'))
        with pytest.raises(ThreatIntelAgentError):
            await agent.correlate(_context())

    asyncio.run(scenario())


def test_context_without_intelligence_is_a_precondition_violation() -> None:
    with pytest.raises(ThreatIntelAgentError):
        ThreatIntelContext(
            investigation_id=InvestigationId("inv-1"),
            objectives=("o",),
            entities=(),
            intelligence=(),
        )


# --------------------------------------------------------------------- assembler


async def _seeded_services():  # noqa: ANN202 - test helper tuple
    investigations = make_investigation_service()
    await investigations.create(
        build_investigation("inv-1", title="Beaconing from HOST-1")
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
    return investigations, graph


def test_assembler_builds_the_seed_with_finding_named_entities() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)

        seed = await assembler.assemble_threat_intel_seed(
            InvestigationId("inv-1")
        )

        assert seed.objectives == ("Investigate: Beaconing from HOST-1",)
        assert [e.display_name for e in seed.entities] == ["HOST-1"]

    asyncio.run(scenario())


def test_assembler_seed_is_valid_without_graph_or_entities() -> None:
    async def scenario() -> None:
        investigations = make_investigation_service()
        await investigations.create(build_investigation("inv-1"))

        seed = await InvestigationStateAssembler(
            investigations
        ).assemble_threat_intel_seed(InvestigationId("inv-1"))

        assert seed.entities == ()
        assert seed.objectives  # objectives alone can still hit knowledge

    asyncio.run(scenario())


# ------------------------------------------------------------------------ flow


def _flow(
    llm_text: str,
    providers: tuple[object, ...],
    assembler: InvestigationStateAssembler,
    trace: RecordingTrace | None = None,
) -> ThreatIntelFlow:
    return ThreatIntelFlow(
        ThreatIntelAgent(ScriptedLLM(llm_text)),
        assembler,
        providers,  # type: ignore[arg-type]
        SequentialIds(),
        FixedClock(),
        trace if trace is not None else RecordingTrace(),
    )


def test_flow_runs_focused_queries_and_traces() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        provider = ScriptedExternalProvider((_intel("T1071"),))
        trace = RecordingTrace()
        flow = _flow(_GOOD_RESPONSE, (provider,), assembler, trace)

        report = await flow.enrich(InvestigationId("inv-1"))

        assert report is not None
        # Focused queries: the objectives plus each entity's display name.
        assert provider.queries == [
            "Investigate: Beaconing from HOST-1",
            "HOST-1",
        ]
        assert len(trace.entries) == 1
        entry = trace.entries[0]
        assert entry.kind is TraceEntryKind.THREAT_INTEL
        assert entry.actor.value == "threat-intel-agent"
        assert "1 external item(s)" in entry.summary
        assert "2 observation(s)" in entry.summary

    asyncio.run(scenario())


def test_flow_skips_quietly_without_external_intelligence() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        trace = RecordingTrace()
        flow = _flow(
            "irrelevant", (ScriptedExternalProvider(()),), assembler, trace
        )

        assert await flow.enrich(InvestigationId("inv-1")) is None
        assert trace.entries == []

    asyncio.run(scenario())


def test_flow_contains_provider_failure_per_provider() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        flow = _flow(
            _GOOD_RESPONSE,
            (FailingExternalProvider(), ScriptedExternalProvider((_intel("T1071"),))),
            assembler,
        )

        report = await flow.enrich(InvestigationId("inv-1"))

        assert report is not None  # the healthy feed still contributed

    asyncio.run(scenario())


def test_flow_dedupes_intelligence_by_origin() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        # Both queries return the same item from the same provider.
        provider = ScriptedExternalProvider((_intel("T1071"),))
        llm = ScriptedLLM('{"summary": "ok", "observations": []}')
        flow = ThreatIntelFlow(
            ThreatIntelAgent(llm),
            assembler,
            (provider,),  # type: ignore[arg-type]
            SequentialIds(),
            FixedClock(),
            RecordingTrace(),
        )

        await flow.enrich(InvestigationId("inv-1"))

        # One deduplicated intelligence line in the prompt.
        assert llm.prompts[0].count("ref=T1071") == 1

    asyncio.run(scenario())


def test_flow_raises_when_the_agent_fails() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        flow = _flow(
            "not json", (ScriptedExternalProvider((_intel("T1071"),)),), assembler
        )

        with pytest.raises(ThreatIntelAgentError):
            await flow.enrich(InvestigationId("inv-1"))

    asyncio.run(scenario())


# ---------------------------------------------------------- runner enrichment


class RecordingLoop:
    def __init__(self) -> None:
        self.states = []

    async def run(self, state):  # noqa: ANN001, ANN201 - protocol duck
        self.states.append(state)
        return "outcome"


class ScriptedThreatIntelFlow:
    def __init__(
        self,
        report: ThreatIntelReport | None = None,
        error: Exception | None = None,
    ) -> None:
        self._report = report
        self._error = error

    async def enrich(
        self, investigation_id: InvestigationId
    ) -> ThreatIntelReport | None:
        if self._error is not None:
            raise self._error
        return self._report


def test_runner_appends_intel_observations_to_the_knowledge() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        loop = RecordingLoop()
        report = ThreatIntelReport(
            investigation_id=InvestigationId("inv-1"),
            observations=(
                ThreatIntelObservation(
                    kind=ThreatIntelObservationKind.ATTACK_MAPPING,
                    detail="Periodic connections match T1071.",
                    references=("T1071",),
                ),
            ),
            summary="C2 suspected",
        )
        runner = InvestigationRunner(
            assembler,
            loop,  # type: ignore[arg-type]
            threat_intel=ScriptedThreatIntelFlow(report),  # type: ignore[arg-type]
        )

        await runner.run(InvestigationId("inv-1"))

        knowledge = loop.states[0].knowledge
        assert knowledge == (
            "[threat-intel] attack_mapping (refs: T1071) "
            "Periodic connections match T1071.",
        )

    asyncio.run(scenario())


def test_runner_contains_a_failed_threat_intel_enrichment() -> None:
    async def scenario() -> None:
        investigations, graph = await _seeded_services()
        assembler = InvestigationStateAssembler(investigations, graph)
        loop = RecordingLoop()
        runner = InvestigationRunner(
            assembler,
            loop,  # type: ignore[arg-type]
            threat_intel=ScriptedThreatIntelFlow(  # type: ignore[arg-type]
                error=ThreatIntelAgentError("correlation failed")
            ),
        )

        await runner.run(InvestigationId("inv-1"))

        # The run proceeded without threat intelligence.
        assert loop.states[0].knowledge == ()

    asyncio.run(scenario())
