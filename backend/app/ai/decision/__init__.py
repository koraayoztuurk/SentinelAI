"""Decision Engine (ES-055).

The Intelligence Layer component that synthesizes an investigation's
confirmed findings into one structured
:class:`~app.domain.investigation_outcome.InvestigationOutcome`
(agent-architecture §6: the Decision Engine is **not** an independent agent).
"""

from app.ai.decision.engine import DecisionEngine

__all__ = ["DecisionEngine"]
