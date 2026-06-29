"""Context Validation.

Validates an assembled Investigation Context before prompt construction
(rag-architecture §9). Only validated context should proceed: an empty context or
an investigation without objectives is reported as an observable issue rather than
silently passed downstream.

Issue codes are a fixed vocabulary, modeled as a closed enum. Richer validation
criteria (conflict detection, evidence-quality and consistency scoring) are
introduced by later specifications.
"""

from dataclasses import dataclass
from enum import Enum

from app.ai.rag.context_builder import InvestigationContext


class ValidationIssueCode(Enum):
    """A context-validation issue code (fixed vocabulary)."""

    MISSING_OBJECTIVES = "missing_objectives"
    EMPTY_CONTEXT = "empty_context"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single, observable context-validation issue."""

    code: ValidationIssueCode
    detail: str


@dataclass(frozen=True, slots=True)
class ContextValidationResult:
    """The outcome of validating an Investigation Context."""

    is_valid: bool
    issues: tuple[ValidationIssue, ...]


class ContextValidator:
    """Validates an Investigation Context (stateless)."""

    def validate(self, context: InvestigationContext) -> ContextValidationResult:
        """Return the validation outcome with any observable issues."""

        issues: list[ValidationIssue] = []
        if not context.objectives:
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.MISSING_OBJECTIVES,
                    detail="Investigation Context defines no objective.",
                )
            )
        if not context.knowledge:
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.EMPTY_CONTEXT,
                    detail="Investigation Context contains no retrieved knowledge.",
                )
            )
        return ContextValidationResult(is_valid=not issues, issues=tuple(issues))
