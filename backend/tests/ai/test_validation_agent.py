"""Tests for the Validation Agent and the Validation Flow (ES-056).

The agent transforms a scripted assessment response into the typed
``ValidationAssessment`` (unknown issue kinds ignored, unknown finding
references un-attributed but preserved, malformed responses raised — an
empty assessment is never a fallback). The flow composes the context
assembler and the Agent Runtime, skipping quietly when there is nothing to
validate. In-memory doubles, plain functions, ``asyncio.run``.
"""

import asyncio

import pytest

from app.ai.agents.validation import (
    ValidationAgent,
    ValidationContext,
    ValidationIssueKind,
)
from app.ai.errors import ValidationAgentError
from app.ai.orchestration.assembler import InvestigationStateAssembler
from app.ai.orchestration.validation import ValidationFlow
from app.domain.enums import FindingStatus
from app.domain.identifiers import (
    EvidenceId,
    FindingId,
    InvestigationId,
)
from app.domain.value_objects import Confidence
from tests.support.builders import (
    build_evidence,
    build_finding,
    build_investigation,
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


def _context() -> ValidationContext:
    from app.ai.agents.validation import EvidenceSnapshot, FindingSnapshot

    return ValidationContext(
        investigation_id=InvestigationId("inv-1"),
        objectives=("Investigate: beaconing",),
        findings=(
            FindingSnapshot(
                id=FindingId("f-1"),
                status="validated",
                confidence=Confidence(0.85),
                supporting_evidence=(EvidenceId("ev-1"),),
            ),
        ),
        evidence=(
            EvidenceSnapshot(
                id=EvidenceId("ev-1"),
                source="edr",
                integrity="verified",
                content="beaconing every 60s",
            ),
        ),
    )


_GOOD_RESPONSE = (
    '{"summary": "One finding lacks corroboration.", "issues": ['
    '{"kind": "missing_evidence", "finding_id": "f-1", '
    '"detail": "No DNS corroboration."}, '
    '{"kind": "unknown_kind", "finding_id": "f-1", "detail": "x"}, '
    '{"kind": "unsupported_conclusion", "finding_id": "ghost", '
    '"detail": "Attribution exceeds the evidence."}]}'
)


def test_assessment_is_typed_filtered_and_attributed() -> None:
    async def scenario() -> None:
        agent = ValidationAgent(ScriptedLLM(_GOOD_RESPONSE))

        assessment = await agent.assess(_context())

        assert assessment.summary == "One finding lacks corroboration."
        assert [f.value for f in assessment.assessed_findings] == ["f-1"]
        # The unknown kind is ignored; the unknown finding reference keeps
        # its observation but loses the invented attribution.
        assert len(assessment.issues) == 2
        first, second = assessment.issues
        assert first.kind is ValidationIssueKind.MISSING_EVIDENCE
        assert first.finding_id == FindingId("f-1")
        assert second.kind is ValidationIssueKind.UNSUPPORTED_CONCLUSION
        assert second.finding_id is None

    asyncio.run(scenario())


def test_reasoning_consumes_findings_and_evidence() -> None:
    async def scenario() -> None:
        llm = ScriptedLLM('{"summary": "ok", "issues": []}')
        agent = ValidationAgent(llm)

        await agent.assess(_context())

        prompt = llm.prompts[0]
        assert "f-1" in prompt
        assert "ev-1" in prompt
        assert "beaconing every 60s" in prompt
        assert "Investigate: beaconing" in prompt

    asyncio.run(scenario())


def test_malformed_response_raises_never_a_clean_bill() -> None:
    async def scenario() -> None:
        agent = ValidationAgent(ScriptedLLM("not json"))
        with pytest.raises(ValidationAgentError):
            await agent.assess(_context())

    asyncio.run(scenario())


def test_missing_issues_list_raises() -> None:
    async def scenario() -> None:
        agent = ValidationAgent(ScriptedLLM('{"summary": "ok"}'))
        with pytest.raises(ValidationAgentError):
            await agent.assess(_context())

    asyncio.run(scenario())


def test_context_without_findings_is_a_precondition_violation() -> None:
    with pytest.raises(ValidationAgentError):
        ValidationContext(
            investigation_id=InvestigationId("inv-1"),
            objectives=("o",),
            findings=(),
            evidence=(),
        )


# ------------------------------------------------------------ validation flow


def test_flow_assembles_and_assesses() -> None:
    async def scenario() -> None:
        service = make_investigation_service()
        await service.create(build_investigation("inv-1", title="Beaconing"))
        await service.attach_evidence(build_evidence("ev-1", "inv-1"))
        await service.create_finding(
            build_finding(
                "f-1",
                "inv-1",
                supporting_evidence=("ev-1",),
                status=FindingStatus.VALIDATED,
            )
        )
        flow = ValidationFlow(
            ValidationAgent(ScriptedLLM('{"summary": "ok", "issues": []}')),
            InvestigationStateAssembler(service),
        )

        assessment = await flow.assess(InvestigationId("inv-1"))

        assert assessment is not None
        assert [f.value for f in assessment.assessed_findings] == ["f-1"]

    asyncio.run(scenario())


def test_flow_skips_quietly_without_findings() -> None:
    async def scenario() -> None:
        service = make_investigation_service()
        await service.create(build_investigation("inv-1"))
        flow = ValidationFlow(
            ValidationAgent(ScriptedLLM('{"summary": "ok", "issues": []}')),
            InvestigationStateAssembler(service),
        )

        assert await flow.assess(InvestigationId("inv-1")) is None

    asyncio.run(scenario())


def test_flow_reraises_contained_agent_failure_with_the_code() -> None:
    async def scenario() -> None:
        service = make_investigation_service()
        await service.create(build_investigation("inv-1"))
        await service.attach_evidence(build_evidence("ev-1", "inv-1"))
        await service.create_finding(
            build_finding("f-1", "inv-1", supporting_evidence=("ev-1",))
        )
        flow = ValidationFlow(
            ValidationAgent(ScriptedLLM("garbage")),
            InvestigationStateAssembler(service),
        )

        with pytest.raises(ValidationAgentError) as excinfo:
            await flow.assess(InvestigationId("inv-1"))
        assert "ai.validation_agent_error" in str(excinfo.value)

    asyncio.run(scenario())
