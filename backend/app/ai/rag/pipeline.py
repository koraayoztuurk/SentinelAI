"""RAG Pipeline orchestrator.

Composes the context-engineering stages into the end-to-end retrieval pipeline
(rag-architecture §4/§18): a Retrieval Plan (ES-012) is executed by the Retriever,
the retrieved knowledge is assembled into an Investigation Context, the context is
validated, and — only when valid — a provider-neutral prompt is built.

The Retriever is the single injected dependency: it is the replaceable port whose
concrete source-backed implementations are deferred. The context-engineering
components (Context Builder, Context Validator, Prompt Builder) are stateless,
dependency-free and owned by the pipeline. The pipeline performs no generation: it
produces the prompt; the actual provider call belongs to the consuming agent
(rag §19). Insufficient context is reported explicitly via
``InsufficientContextError``.
"""

import logging
from dataclasses import dataclass

from app.ai.agents.memory.plan import RetrievalPlan
from app.ai.agents.planner.state import InvestigationState
from app.ai.errors import InsufficientContextError
from app.ai.rag.context_builder import ContextBuilder, InvestigationContext
from app.ai.rag.prompt_builder import Prompt, PromptBuilder
from app.ai.rag.retriever import Retriever
from app.ai.rag.validation import ContextValidator

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RagResult:
    """The product of one RAG pipeline run: validated context and its prompt."""

    context: InvestigationContext
    prompt: Prompt


class RagPipeline:
    """Runs the retrieve → build → validate → prompt pipeline."""

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever
        self._context_builder = ContextBuilder()
        self._validator = ContextValidator()
        self._prompt_builder = PromptBuilder()

    async def run(
        self, state: InvestigationState, plan: RetrievalPlan
    ) -> RagResult:
        """Assemble and validate context, then build its prompt."""

        retrieved = await self._retriever.retrieve(state, plan)
        context = self._context_builder.build(state, retrieved)
        validation = self._validator.validate(context)
        if not validation.is_valid:
            codes = [issue.code.value for issue in validation.issues]
            raise InsufficientContextError(
                f"Investigation context failed validation: {codes}."
            )
        prompt = self._prompt_builder.build(context)
        logger.info(
            "rag pipeline produced context investigation_id=%s knowledge_items=%s",
            context.investigation_id.value,
            len(context.knowledge),
        )
        return RagResult(context=context, prompt=prompt)
