"""Behavioral validation of the Validation Agent (ES-056, ai-validation).

The agent never fabricates a clean bill of health: every adversarial provider
response raises rather than resolving to an empty assessment; recognized
issues survive partial recognition; the reasoning input demonstrably derives
from the assembled findings and evidence; equivalent inputs yield an
equivalent assessment.
"""

import asyncio

import pytest

from app.ai.agents.validation import (
    EvidenceSnapshot,
    FindingSnapshot,
    ValidationAgent,
    ValidationContext,
    ValidationIssueKind,
)
from app.ai.errors import ValidationAgentError
from app.domain.identifiers import EvidenceId, FindingId, InvestigationId
from app.domain.value_objects import Confidence
from tests.ai_validation.support import (
    ADVERSARIAL_RESPONSES,
    RecordingLLM,
    ScriptedLLM,
)

pytestmark = pytest.mark.ai


def _context() -> ValidationContext:
    return ValidationContext(
        investigation_id=InvestigationId("inv-9"),
        objectives=("Investigate: beaconing",),
        findings=(
            FindingSnapshot(
                id=FindingId("f-1"),
                status="validated",
                confidence=Confidence(0.8),
                supporting_evidence=(EvidenceId("ev-1"),),
            ),
        ),
        evidence=(
            EvidenceSnapshot(
                id=EvidenceId("ev-1"),
                source="edr",
                integrity="verified",
                content="periodic TLS beacon",
            ),
        ),
    )


def test_adversarial_responses_never_resolve_to_a_clean_bill() -> None:
    async def scenario() -> None:
        for response in ADVERSARIAL_RESPONSES:
            agent = ValidationAgent(ScriptedLLM(response))
            with pytest.raises(ValidationAgentError):
                await agent.assess(_context())

    asyncio.run(scenario())


def test_partial_recognition_preserves_recognized_issues() -> None:
    async def scenario() -> None:
        agent = ValidationAgent(
            ScriptedLLM(
                '{"summary": "mixed", "issues": ['
                '{"kind": "missing_evidence", "finding_id": "f-1", '
                '"detail": "no DNS"}, '
                '{"kind": "made_up_kind", "detail": "x"}, '
                '"not even a dict", '
                '{"kind": "conflicting_observations", "detail": ""}]}'
            )
        )

        assessment = await agent.assess(_context())

        assert len(assessment.issues) == 1
        assert assessment.issues[0].kind is (
            ValidationIssueKind.MISSING_EVIDENCE
        )

    asyncio.run(scenario())


def test_reasoning_consumes_the_assembled_material() -> None:
    async def scenario() -> None:
        llm = RecordingLLM('{"summary": "ok", "issues": []}')
        await ValidationAgent(llm).assess(_context())

        prompt = llm.requests[0].prompt
        assert "inv-9" in prompt
        assert "f-1" in prompt
        assert "periodic TLS beacon" in prompt

    asyncio.run(scenario())


def test_equivalent_inputs_yield_an_equivalent_assessment() -> None:
    async def scenario() -> None:
        response = (
            '{"summary": "one gap", "issues": [{"kind": "missing_evidence", '
            '"finding_id": "f-1", "detail": "no corroboration"}]}'
        )
        first = await ValidationAgent(ScriptedLLM(response)).assess(_context())
        second = await ValidationAgent(ScriptedLLM(response)).assess(
            _context()
        )

        assert first == second

    asyncio.run(scenario())
