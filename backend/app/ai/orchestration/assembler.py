"""Concrete Investigation State assembler (ES-044).

First realization of the Investigation Workspace / Context Builder
responsibility (planner-agent §4): assembles the
:class:`~app.ai.agents.planner.state.InvestigationState` the Planner Agent
reasons over from the Investigation Service's data — the AI Runtime composes
backend service interfaces one way (ADR-010) and never touches persistence.

Assembly decisions (ES-044, recorded in the tracker):

- **Objectives** — a single objective derived from the investigation title
  (the platform has no separate objective source yet).
- **Confidence** — the highest finding confidence, ``0.0`` with no findings
  (the state's confidence reflects the strongest supported conclusion).
- **History** — the most recent trace entries as ``kind: summary`` lines
  (bounded), so the agent observes what already happened, including its own
  earlier decisions.
- **Tasks** — empty: no Task service exists (tracker: Task ownership is an
  open documentation gap).
"""

from app.ai.agents.planner.state import InvestigationState
from app.application.investigation import InvestigationService
from app.application.planner.actions import ExecutionResult
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence

_HISTORY_LIMIT = 10


class InvestigationStateAssembler:
    """Assembles Investigation States from the Investigation Service."""

    def __init__(self, investigations: InvestigationService) -> None:
        self._investigations = investigations

    async def assemble(
        self, investigation_id: InvestigationId
    ) -> InvestigationState:
        """Assemble the current state snapshot of an investigation."""

        investigation = await self._investigations.get(investigation_id)
        evidence = await self._investigations.list_evidence(investigation_id)
        findings = await self._investigations.list_findings(investigation_id)
        trace = await self._investigations.list_trace(investigation_id)

        confidence = max(
            (finding.confidence.value for finding in findings), default=0.0
        )
        history = tuple(
            f"{entry.kind.value}: {entry.summary}"
            for entry in trace[-_HISTORY_LIMIT:]
        )
        return InvestigationState(
            investigation_id=investigation_id,
            status=investigation.status.value,
            confidence=Confidence(confidence),
            objectives=(f"Investigate: {investigation.title}",),
            evidence_ids=tuple(item.id for item in evidence),
            finding_ids=tuple(finding.id for finding in findings),
            history=history,
        )

    async def next_state(
        self, state: InvestigationState, result: ExecutionResult
    ) -> InvestigationState:
        """Re-assemble after an executed action (the loop's ``StateAssembler``)."""

        return await self.assemble(state.investigation_id)
