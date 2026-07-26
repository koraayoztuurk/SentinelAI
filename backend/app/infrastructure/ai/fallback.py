"""Cross-provider LLM fallback chain (ES-067).

With two concrete LLM adapters available (Gemini since ES-043, NVIDIA NIM since
ES-054), a capacity outage on one — the multi-hour Gemini ``generateContent``
503 windows observed during ES-051/053 — can be served by the other instead of
escalating the run.

This composite is itself an :class:`~app.ai.providers.llm.LLMProvider`, so it
composes at the root without any consumer knowing: the agents, the loop and the
Decision Engine keep depending on the provider-neutral port (ADR-005). It sits
*above* the per-adapter resilience layer (ES-067,
:mod:`app.infrastructure.ai.resilience`), so the primary has already spent its
retry budget — and, once its circuit opens, fails fast — before the secondary is
asked. That ordering is what keeps a failover cheap rather than additive.

Health stays observable (ADR-013's rationale: breakers must not mask provider
health). Every failover increments a counter rendered on ``/metrics``, and both
the failover and a total outage are logged with the failing provider's name. A
run served by the secondary is a *degraded* success, and the operator can see
it.

When the secondary fails too, the raised ``LLMProviderError`` names both
providers and the loop degrades to ESCALATED exactly as it does today
(ADR-013 §3) — the chain adds an attempt, never a new failure mode.
"""

import logging

from app.ai.errors import LLMProviderError
from app.ai.providers.llm import LLMProvider, LLMRequest, LLMResponse
from app.observability.metrics import metrics

logger = logging.getLogger(__name__)


class FallbackLLMProvider:
    """Serves through ``primary``, falling back to ``secondary`` on failure."""

    def __init__(
        self,
        primary: LLMProvider,
        secondary: LLMProvider,
        primary_name: str,
        secondary_name: str,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._primary_name = primary_name
        self._secondary_name = secondary_name

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate through the primary, or the secondary if it cannot."""

        try:
            return await self._primary.generate(request)
        except LLMProviderError as primary_error:
            metrics.record_llm_fallback(
                self._primary_name, self._secondary_name
            )
            logger.warning(
                "llm provider fallback engaged primary=%s secondary=%s",
                self._primary_name,
                self._secondary_name,
            )
            try:
                return await self._secondary.generate(request)
            except LLMProviderError as secondary_error:
                # Both providers are down: report both so the operator sees a
                # platform-wide outage rather than one provider's message.
                raise LLMProviderError(
                    f"Both LLM providers failed — {self._primary_name}: "
                    f"{primary_error.message} | {self._secondary_name}: "
                    f"{secondary_error.message}"
                ) from secondary_error
