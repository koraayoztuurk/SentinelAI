"""Investigation run entry point (ES-044).

The invocation surface ADR-010 anticipated: assemble the initial Investigation
State, then run the Investigation Loop over it. This is the single composition
the presentation run endpoint delegates to; it adds no behaviour of its own.
"""

from app.ai.orchestration.assembler import InvestigationStateAssembler
from app.ai.orchestration.loop import InvestigationLoop, LoopOutcome
from app.domain.identifiers import InvestigationId


class InvestigationRunner:
    """Assembles the initial state and runs the Investigation Loop."""

    def __init__(
        self, assembler: InvestigationStateAssembler, loop: InvestigationLoop
    ) -> None:
        self._assembler = assembler
        self._loop = loop

    async def run(self, investigation_id: InvestigationId) -> LoopOutcome:
        """Run the loop for one investigation and return its outcome."""

        state = await self._assembler.assemble(investigation_id)
        return await self._loop.run(state)
