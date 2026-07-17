"""Behavioral validation of the Threat Intelligence Agent (ES-059, ai-validation).

The agent never presents external intelligence the platform did not retrieve:
every adversarial provider response raises rather than resolving to a silent
empty report; fabricated references are discarded from provenance; the
reasoning input demonstrably derives from the assembled context; equivalent
inputs yield an equivalent report.
"""

import asyncio

import pytest

from app.ai.agents.threat_intel import (
    ThreatIntelAgent,
    ThreatIntelContext,
    ThreatIntelEntity,
)
from app.ai.errors import ThreatIntelAgentError
from app.ai.providers.external import ExternalKnowledgeItem
from app.domain.identifiers import EntityId, InvestigationId
from app.domain.value_objects import Confidence
from tests.ai_validation.support import (
    ADVERSARIAL_RESPONSES,
    RecordingLLM,
    ScriptedLLM,
)

pytestmark = pytest.mark.ai


def _context() -> ThreatIntelContext:
    return ThreatIntelContext(
        investigation_id=InvestigationId("inv-9"),
        objectives=("Investigate: beaconing",),
        entities=(
            ThreatIntelEntity(
                id=EntityId("host-1"), type="endpoint", display_name="HOST-1"
            ),
        ),
        intelligence=(
            ExternalKnowledgeItem(
                source="mitre-attack",
                reference="T1071",
                content="Application Layer Protocol: C2 over common protocols.",
                confidence=Confidence(0.6),
            ),
        ),
    )


def test_adversarial_responses_never_resolve_to_a_report() -> None:
    async def scenario() -> None:
        for response in ADVERSARIAL_RESPONSES:
            agent = ThreatIntelAgent(ScriptedLLM(response))
            with pytest.raises(ThreatIntelAgentError):
                await agent.correlate(_context())

    asyncio.run(scenario())


def test_fabricated_references_are_never_attributed() -> None:
    async def scenario() -> None:
        agent = ThreatIntelAgent(
            ScriptedLLM(
                '{"summary": "s", "observations": ['
                '{"kind": "cve_correlation", '
                '"references": ["CVE-2099-0001", "T9999"], '
                '"detail": "invented intelligence"}]}'
            )
        )

        report = await agent.correlate(_context())

        # The observation survives; its invented provenance does not.
        assert len(report.observations) == 1
        assert report.observations[0].references == ()

    asyncio.run(scenario())


def test_reasoning_input_derives_from_the_assembled_context() -> None:
    async def scenario() -> None:
        llm = RecordingLLM('{"summary": "ok", "observations": []}')
        await ThreatIntelAgent(llm).correlate(_context())

        prompt = llm.requests[0].prompt
        assert "T1071" in prompt
        assert "HOST-1" in prompt
        assert "Investigate: beaconing" in prompt
        # The vocabulary the transformation accepts is named to the provider.
        for kind in (
            "ioc_enrichment",
            "cve_correlation",
            "attack_mapping",
            "threat_actor",
        ):
            assert kind in prompt

    asyncio.run(scenario())


def test_equivalent_inputs_yield_an_equivalent_report() -> None:
    async def scenario() -> None:
        response = (
            '{"summary": "stable", "observations": ['
            '{"kind": "attack_mapping", "references": ["T1071"], '
            '"detail": "match"}]}'
        )
        first = await ThreatIntelAgent(ScriptedLLM(response)).correlate(
            _context()
        )
        second = await ThreatIntelAgent(ScriptedLLM(response)).correlate(
            _context()
        )

        assert first == second

    asyncio.run(scenario())
