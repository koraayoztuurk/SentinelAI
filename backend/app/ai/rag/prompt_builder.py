"""Prompt Builder.

Transforms a validated Investigation Context into a structured, model-independent
prompt (rag-architecture §10). Prompt construction is deliberately kept
**provider-neutral**: it produces an AI-layer ``Prompt`` artifact rather than a
provider request, preserving the boundary between retrieval/context engineering
and generation (rag §19). The consuming agent wraps the ``Prompt`` into a concrete
provider request (for example the ES-009 ``LLMRequest``).

The prompt preserves provenance: each knowledge line carries its strategy, source
and reference so generated responses remain traceable. Output is deterministic for
equivalent context.
"""

from dataclasses import dataclass

from app.ai.rag.context_builder import InvestigationContext


@dataclass(frozen=True, slots=True)
class Prompt:
    """A provider-neutral prompt artifact produced from investigation context."""

    text: str


class PromptBuilder:
    """Builds a provider-neutral Prompt from an Investigation Context (stateless)."""

    def build(self, context: InvestigationContext) -> Prompt:
        """Assemble a deterministic, provenance-preserving prompt."""

        lines = [
            f"investigation_id={context.investigation_id.value}",
            f"confidence={context.confidence.value}",
            f"objectives={list(context.objectives)}",
            "knowledge:",
        ]
        for item in context.knowledge:
            lines.append(
                f"- [{item.strategy.value}] {item.source}/{item.reference} "
                f"(confidence={item.confidence.value}): {item.content}"
            )
        return Prompt(text="\n".join(lines))
