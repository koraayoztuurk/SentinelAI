"""Language-model provider port.

Defines the provider-neutral language-model interface the AI Runtime depends on
(ADR-005, agent-architecture §6a). The request and response are intentionally
minimal typed objects: wrapping the input/output lets the contract evolve
(message/role formats, parameters, streaming, structured output) without changing
the method signature.

This contract must remain entirely provider-neutral. It must not expose OpenAI-,
Anthropic-, Gemini- or any other vendor-specific concepts, parameters or types.
Concrete providers are introduced by later specifications.

Resilience contract (ADR-013): implementations must enforce a bounded execution
time; exceeding the bound — like any provider failure — is surfaced as
:class:`~app.ai.errors.LLMProviderError`, never as an indefinite hang. Timeout
values are configuration; the existence of the bound is the contract.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """A provider-neutral request to a language model (intentionally minimal)."""

    prompt: str


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """A provider-neutral language-model response (intentionally minimal)."""

    text: str


class LLMProvider(Protocol):
    """Replaceable language-model provider interface."""

    async def generate(self, request: LLMRequest) -> LLMResponse: ...
