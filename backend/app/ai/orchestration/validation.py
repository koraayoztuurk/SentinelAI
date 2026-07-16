"""Validation Flow (ES-056).

The AI Runtime composition that runs the Validation Agent over an
investigation's assembled findings and evidence (agent-architecture §6:
validation improves trustworthiness before final decisions are synthesized).
The agent runs through the **Agent Runtime** — the single execution path
(ADR-013); a contained agent failure is re-raised as
:class:`~app.ai.errors.ValidationAgentError` carrying the stable code —
like the Retrieval Flow, this composition has no degrade product (an empty
assessment would read as a clean bill of health); its caller decides how to
contain the failure.

``None`` signals there was nothing to validate (an investigation without
findings) — a quiet skip, not a failure.
"""

import logging
from typing import Protocol

from app.ai.agents.runtime import AgentRuntime
from app.ai.agents.validation.agent import (
    ValidationAgent,
    ValidationAssessmentRequest,
)
from app.ai.agents.validation.assessment import (
    ValidationAssessment,
    ValidationContext,
)
from app.ai.errors import ValidationAgentError
from app.domain.identifiers import InvestigationId

logger = logging.getLogger(__name__)


class ValidationContextAssembler(Protocol):
    """Assembles the material under validation (Workspace / Context Builder)."""

    async def assemble_validation_context(
        self, investigation_id: InvestigationId
    ) -> ValidationContext | None: ...


class ValidationFlow:
    """Runs the Validation Agent over the assembled context (stateless)."""

    def __init__(
        self,
        agent: ValidationAgent,
        assembler: ValidationContextAssembler,
    ) -> None:
        self._agent = agent
        self._assembler = assembler
        self._runtime = AgentRuntime()

    async def assess(
        self, investigation_id: InvestigationId
    ) -> ValidationAssessment | None:
        """Assess the investigation's findings; ``None`` when there are none."""

        context = await self._assembler.assemble_validation_context(
            investigation_id
        )
        if context is None:
            logger.info(
                "validation skipped (no findings) investigation_id=%s",
                investigation_id.value,
            )
            return None

        result = await self._runtime.run(
            self._agent, ValidationAssessmentRequest(context=context)
        )
        if result.product is None:
            raise ValidationAgentError(
                f"Validation failed ({result.error})."
            )
        logger.info(
            "validation flow completed investigation_id=%s issues=%s",
            investigation_id.value,
            len(result.product.issues),
        )
        return result.product
