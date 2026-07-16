"""Decision Engine (ES-055).

Synthesizes the structured Investigation Outcome from an investigation's
**confirmed** findings (agent-architecture §6, system-overview §Decision
Engine): conflict identification, overall confidence estimation and a
recommendation, produced as one ``InvestigationOutcome`` (status
``SYNTHESIZED``) — the read-only outcome surface (ES-045) gains its writer.

Boundaries (documented):

- **Not an agent** — an Intelligence Layer component executing within the AI
  Runtime after the Planner determines the investigation is complete
  (planner-agent §7: "Investigation Complete? → Decision Engine"). It
  performs synthesis, never specialized analysis.
- **Synthesis, never invention** — the engine reasons only over the provided
  findings; contributing-finding references outside the confirmed set are
  discarded, and a malformed synthesis response raises
  :class:`~app.ai.errors.DecisionEngineError` rather than fabricating a
  partial outcome (no safe fallback recommendation exists).
- **Recommendations only** — the outcome is advisory; final decisions remain
  the analyst's (human oversight).
- **AI → Application, one way** (ADR-010): findings and outcome persistence
  are reached through the Investigation Service interface; identifiers and
  timestamps are caller-supplied through the ``IdSource``/``Clock`` ports.

Skip conditions (returning ``None``, logged): an outcome already exists
(0..1 per investigation — re-runs must not burn provider calls), or the
investigation has no confirmed (validated/accepted) finding — an outcome
without supporting findings would contradict its finding-backed definition.
"""

import json
import logging

from app.ai.agents.planner.state import InvestigationState
from app.ai.agents.validation.assessment import ValidationAssessment
from app.ai.errors import DecisionEngineError
from app.ai.orchestration.tracing import Clock, IdSource
from app.ai.providers.llm import LLMProvider, LLMRequest
from app.application.investigation import (
    InvestigationService,
    OutcomeNotFoundError,
)
from app.domain.enums import (
    FindingStatus,
    InvestigationOutcomeStatus,
)
from app.domain.finding import Finding
from app.domain.identifiers import InvestigationOutcomeId
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.value_objects import Confidence

logger = logging.getLogger(__name__)

_CONFIRMED = (FindingStatus.VALIDATED, FindingStatus.ACCEPTED)
# Resource bounds on list fields quoted from the provider response.
_LIST_LIMIT = 10


class DecisionEngine:
    """Synthesizes one Investigation Outcome from confirmed findings."""

    def __init__(
        self,
        llm: LLMProvider,
        investigations: InvestigationService,
        ids: IdSource,
        clock: Clock,
    ) -> None:
        self._llm = llm
        self._investigations = investigations
        self._ids = ids
        self._clock = clock

    async def synthesize(
        self,
        state: InvestigationState,
        assessment: ValidationAssessment | None = None,
    ) -> InvestigationOutcome | None:
        """Synthesize and persist the investigation's outcome (0..1).

        Returns the persisted outcome, or ``None`` when synthesis is skipped
        (an outcome already exists, or no confirmed finding supports one).
        ``assessment`` carries the Validation Agent's findings assessment
        when validation ran (ES-056) — the documented Decision Engine input
        ("validated agent findings"); its issues inform the synthesis.
        Malformed provider output raises ``DecisionEngineError``.
        """

        investigation_id = state.investigation_id
        try:
            await self._investigations.get_outcome(investigation_id)
        except OutcomeNotFoundError:
            pass
        else:
            logger.info(
                "outcome synthesis skipped (outcome exists) investigation_id=%s",
                investigation_id.value,
            )
            return None

        findings = await self._investigations.list_findings(investigation_id)
        confirmed = tuple(f for f in findings if f.status in _CONFIRMED)
        if not confirmed:
            logger.info(
                "outcome synthesis skipped (no confirmed findings) "
                "investigation_id=%s",
                investigation_id.value,
            )
            return None

        response = await self._llm.generate(
            self._build_request(state, confirmed, assessment)
        )
        outcome = self._to_outcome(response.text, state, confirmed)
        created = await self._investigations.create_outcome(outcome)
        logger.info(
            "outcome synthesized id=%s investigation_id=%s confidence=%s",
            created.id.value,
            investigation_id.value,
            created.confidence.value,
        )
        return created

    @staticmethod
    def _build_request(
        state: InvestigationState,
        confirmed: tuple[Finding, ...],
        assessment: ValidationAssessment | None,
    ) -> LLMRequest:
        # Prompt content is an implementation detail of the documented
        # synthesis boundary; it names the exact JSON shape `_to_outcome`
        # accepts so a real provider can play (the ES-044/054 precedent).
        finding_lines = "\n".join(
            f"- id={finding.id.value} status={finding.status.value} "
            f"confidence={finding.confidence.value} "
            f"entities={[e.value for e in finding.related_entities]}"
            for finding in confirmed
        )
        if assessment is None:
            validation_section = "validation_assessment=not available"
        else:
            issue_lines = "\n".join(
                f"- kind={issue.kind.value} "
                f"finding={issue.finding_id.value if issue.finding_id else '-'}"
                f" detail={issue.detail}"
                for issue in assessment.issues
            )
            validation_section = (
                f"validation_summary={assessment.summary}\n"
                "validation_issues:\n"
                f"{issue_lines if issue_lines else '- none'}"
            )
        prompt = (
            "You are the decision engine of a security investigation "
            "platform. Synthesize the confirmed findings below into one "
            "coherent investigation outcome and respond with ONLY a JSON "
            "object (no prose, no code fences), of exactly this shape:\n"
            '{"recommendation": "<concise analyst recommendation>", '
            '"confidence": <0.0-1.0>, '
            '"contributing_findings": ["<finding id>"], '
            '"detected_conflicts": ["<conflicting observations, if any>"], '
            '"open_questions": ["<unresolved questions, if any>"]}\n'
            "Base the synthesis only on the findings and context provided; "
            "list conflicts and open questions honestly rather than "
            "overstating confidence.\n"
            "Investigation state:\n"
            f"investigation_id={state.investigation_id.value}\n"
            f"status={state.status}\n"
            f"objectives={list(state.objectives)}\n"
            f"confidence={state.confidence.value}\n"
            "Confirmed findings:\n"
            f"{finding_lines}\n"
            f"{validation_section}\n"
            f"retrieved_knowledge={list(state.knowledge)}\n"
            f"history={list(state.history)}"
        )
        return LLMRequest(prompt=prompt)

    def _to_outcome(
        self,
        text: str,
        state: InvestigationState,
        confirmed: tuple[Finding, ...],
    ) -> InvestigationOutcome:
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise DecisionEngineError(
                "Decision Engine received a malformed (non-JSON) synthesis "
                "response."
            ) from exc
        if not isinstance(payload, dict):
            raise DecisionEngineError(
                "Decision Engine received an unexpected synthesis shape."
            )

        recommendation = payload.get("recommendation")
        if not isinstance(recommendation, str) or not recommendation.strip():
            raise DecisionEngineError(
                "Decision Engine synthesis carries no recommendation."
            )

        confidence_raw = payload.get("confidence")
        if isinstance(confidence_raw, bool) or not isinstance(
            confidence_raw, (int, float)
        ):
            raise DecisionEngineError(
                "Decision Engine synthesis carries no numeric confidence."
            )
        confidence = Confidence(min(1.0, max(0.0, float(confidence_raw))))

        # Contributing findings: references outside the confirmed set are
        # discarded (never invented); an absent/empty selection attributes
        # the outcome to every confirmed finding (deterministic completion).
        known = {finding.id.value: finding.id for finding in confirmed}
        raw_refs = payload.get("contributing_findings")
        contributing = tuple(
            known[ref]
            for ref in raw_refs
            if isinstance(ref, str) and ref in known
        ) if isinstance(raw_refs, list) else ()
        if not contributing:
            contributing = tuple(finding.id for finding in confirmed)

        return InvestigationOutcome(
            id=InvestigationOutcomeId(self._ids.new_id()),
            investigation_id=state.investigation_id,
            confidence=confidence,
            recommendation=recommendation.strip(),
            status=InvestigationOutcomeStatus.SYNTHESIZED,
            created_at=self._clock.now(),
            contributing_findings=contributing,
            detected_conflicts=self._string_list(
                payload.get("detected_conflicts")
            ),
            open_questions=self._string_list(payload.get("open_questions")),
        )

    @staticmethod
    def _string_list(value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        items = [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]
        return tuple(items[:_LIST_LIMIT])
