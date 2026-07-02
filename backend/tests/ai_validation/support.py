"""Shared deterministic fakes for the AI Validation suite (ES-035).

Behavioral validation exercises the AI capabilities over scripted, deterministic
provider doubles — no live AI calls (ai-validation §2/§7: technology independence,
independent verification).
"""

from app.ai import InvestigationState, LLMRequest, LLMResponse
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence


class ScriptedLLM:
    """Deterministic LLM provider double returning a fixed response."""

    def __init__(self, text: str) -> None:
        self._text = text

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=self._text)


class RecordingLLM(ScriptedLLM):
    """Scripted LLM that also records every request it receives."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return await super().generate(request)


def make_state(
    investigation_id: str = "inv-1",
    objectives: tuple[str, ...] = ("determine malicious activity",),
) -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId(investigation_id),
        status="active",
        confidence=Confidence(0.5),
        objectives=objectives,
    )


# Structured provider responses no reasoning contract covers: arbitrary text,
# wrong JSON shapes, wrong field types, unknown vocabulary. Behavioral validation
# requires the agents to degrade safely over all of them.
ADVERSARIAL_RESPONSES = (
    "",
    "not json at all",
    "null",
    "42",
    "true",
    '"a bare string"',
    "[1, 2, 3]",
    '{"action": null}',
    '{"action": 42}',
    '{"action": "unknown_action"}',
    '{"strategies": "not a list"}',
    '{"strategies": [42, null, {}]}',
    '{"unrelated": {"deeply": ["nested", "junk"]}}',
)
