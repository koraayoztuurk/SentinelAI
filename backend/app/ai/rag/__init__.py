"""RAG Pipeline: context engineering for AI reasoning.

Assembles trustworthy investigation context from retrieved knowledge and produces
a provider-neutral prompt (rag-architecture). The Retriever is a replaceable port;
concrete source-backed retrievers are introduced by later specifications.
"""

from app.ai.rag.context_builder import ContextBuilder, InvestigationContext
from app.ai.rag.pipeline import RagPipeline, RagResult
from app.ai.rag.prompt_builder import Prompt, PromptBuilder
from app.ai.rag.retriever import (
    RetrievedItem,
    RetrievedKnowledge,
    Retriever,
)
from app.ai.rag.validation import (
    ContextValidationResult,
    ContextValidator,
    ValidationIssue,
    ValidationIssueCode,
)

__all__ = [
    "Retriever",
    "RetrievedItem",
    "RetrievedKnowledge",
    "ContextBuilder",
    "InvestigationContext",
    "ContextValidator",
    "ContextValidationResult",
    "ValidationIssue",
    "ValidationIssueCode",
    "PromptBuilder",
    "Prompt",
    "RagPipeline",
    "RagResult",
]
