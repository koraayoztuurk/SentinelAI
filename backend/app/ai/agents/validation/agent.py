"""Validation Agent (ES-056).

The concrete ``validation-agent`` that evaluates an investigation's findings
against their supporting evidence (agent-architecture §6) and produces one
typed :class:`~app.ai.agents.validation.assessment.ValidationAssessment`
via the AI Foundation LLM provider. Validation improves trustworthiness
before final decisions are synthesized (the Decision Engine consumes the
assessment); it never mutates findings and never calls services.

Reasoning boundary: the agent builds a provider request from the assembled
``ValidationContext``, obtains a provider response, and transforms a minimal
structured (JSON) response into the typed assessment. Unknown issue kinds are
ignored; an issue referencing an unknown finding keeps its observation with
``finding_id=None`` (the detail is preserved, the attribution is not
invented). A malformed response raises
:class:`~app.ai.errors.ValidationAgentError` — an empty assessment is not a
neutral fallback (it would read as a clean bill of health).
"""

import json
import logging
from dataclasses import dataclass

from app.ai.agents.base import AgentIdentity
from app.ai.agents.validation.assessment import (
    ValidationAssessment,
    ValidationContext,
    ValidationIssue,
    ValidationIssueKind,
)
from app.ai.errors import ValidationAgentError
from app.ai.providers.llm import LLMProvider, LLMRequest

logger = logging.getLogger(__name__)

VALIDATION_AGENT_IDENTITY = AgentIdentity("validation-agent")

# Resource bound on reported issues (mirrors the Decision Engine's list bound).
_ISSUE_LIMIT = 10


@dataclass(frozen=True, slots=True)
class ValidationAssessmentRequest:
    """The typed execution request of the Validation Agent (ADR-013)."""

    context: ValidationContext


class ValidationAgent:
    """Assesses findings against their evidence (stateless)."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @property
    def identity(self) -> AgentIdentity:
        return VALIDATION_AGENT_IDENTITY

    async def execute(
        self, request: ValidationAssessmentRequest
    ) -> ValidationAssessment:
        """Run one assessment through the typed agent contract (ADR-013)."""

        return await self.assess(request.context)

    async def assess(self, context: ValidationContext) -> ValidationAssessment:
        """Reason over the assembled context and return one assessment."""

        response = await self._llm.generate(self._build_request(context))
        assessment = self._to_assessment(response.text, context)
        logger.info(
            "validation agent assessed investigation_id=%s findings=%s "
            "issues=%s",
            context.investigation_id.value,
            len(assessment.assessed_findings),
            len(assessment.issues),
        )
        return assessment

    @staticmethod
    def _build_request(context: ValidationContext) -> LLMRequest:
        # Prompt content is an implementation detail of the documented
        # transformation boundary; it names the exact JSON shape and issue
        # vocabulary `_to_assessment` accepts (the ES-044/054 precedent).
        finding_lines = "\n".join(
            f"- id={finding.id.value} status={finding.status} "
            f"confidence={finding.confidence.value} "
            f"evidence={[e.value for e in finding.supporting_evidence]}"
            for finding in context.findings
        )
        evidence_lines = "\n".join(
            f"- id={item.id.value} source={item.source} "
            f"integrity={item.integrity} content={item.content}"
            for item in context.evidence
        )
        prompt = (
            "You are the validation agent of a security investigation "
            "platform. Evaluate whether each finding below is consistent "
            "with and supported by the evidence, and respond with ONLY a "
            "JSON object (no prose, no code fences), of exactly this "
            "shape:\n"
            '{"summary": "<one-line overall assessment>", '
            '"issues": [{"kind": "<one of: factual_inconsistency, '
            "missing_evidence, conflicting_observations, "
            'unsupported_conclusion>", "finding_id": "<finding id or '
            'null>", "detail": "<what is wrong>"}]}\n'
            "Report an empty issues list only when every finding is "
            "genuinely supported; never invent issues.\n"
            "Investigation state:\n"
            f"investigation_id={context.investigation_id.value}\n"
            f"objectives={list(context.objectives)}\n"
            "Findings under validation:\n"
            f"{finding_lines}\n"
            "Evidence:\n"
            f"{evidence_lines}"
        )
        return LLMRequest(prompt=prompt)

    @staticmethod
    def _to_assessment(
        text: str, context: ValidationContext
    ) -> ValidationAssessment:
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise ValidationAgentError(
                "Validation Agent received a malformed (non-JSON) "
                "assessment response."
            ) from exc
        if not isinstance(payload, dict):
            raise ValidationAgentError(
                "Validation Agent received an unexpected assessment shape."
            )

        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValidationAgentError(
                "Validation Agent assessment carries no summary."
            )

        known = {finding.id.value: finding.id for finding in context.findings}
        issues: list[ValidationIssue] = []
        raw_issues = payload.get("issues")
        if not isinstance(raw_issues, list):
            raise ValidationAgentError(
                "Validation Agent assessment carries no issues list."
            )
        for raw in raw_issues:
            if not isinstance(raw, dict):
                continue
            kind_token = raw.get("kind")
            detail = raw.get("detail")
            if not isinstance(kind_token, str) or not isinstance(detail, str):
                continue
            if not detail.strip():
                continue
            try:
                kind = ValidationIssueKind(kind_token)
            except ValueError:
                # Unknown issue kinds are ignored (fixed vocabulary).
                continue
            reference = raw.get("finding_id")
            finding_id = (
                known.get(reference) if isinstance(reference, str) else None
            )
            issues.append(
                ValidationIssue(
                    kind=kind,
                    detail=detail.strip(),
                    finding_id=finding_id,
                )
            )
            if len(issues) >= _ISSUE_LIMIT:
                break

        return ValidationAssessment(
            investigation_id=context.investigation_id,
            assessed_findings=tuple(f.id for f in context.findings),
            issues=tuple(issues),
            summary=summary.strip(),
        )
