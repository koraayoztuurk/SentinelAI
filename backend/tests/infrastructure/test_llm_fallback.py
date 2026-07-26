"""Tests for the cross-provider LLM fallback chain (ES-067).

Deterministic over scripted provider doubles: the primary serves when it can,
the secondary serves when the primary cannot, a total outage still degrades
through the documented ``LLMProviderError`` path (ADR-013 §3), and every
failover is counted so the breaker cannot hide provider health.
"""

import asyncio

import pytest

from app.ai.errors import LLMProviderError
from app.ai.providers.llm import LLMRequest, LLMResponse
from app.infrastructure.ai.fallback import FallbackLLMProvider
from app.observability.metrics import PlatformMetrics, metrics

_REQUEST = LLMRequest(prompt="assess the beaconing pattern")


class _ScriptedLLM:
    def __init__(self, text: str | None = None, error: str | None = None) -> None:
        self._text = text
        self._error = error
        self.calls = 0

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        if self._error is not None:
            raise LLMProviderError(self._error)
        return LLMResponse(text=self._text or "")


def _chain(primary: _ScriptedLLM, secondary: _ScriptedLLM) -> FallbackLLMProvider:
    return FallbackLLMProvider(primary, secondary, "gemini", "nvidia")


@pytest.fixture(autouse=True)
def _fresh_metrics() -> None:
    # The registry is process-wide; reset the counters this module asserts on.
    metrics.__dict__.update(PlatformMetrics().__dict__)


def test_healthy_primary_serves_and_secondary_is_never_called() -> None:
    primary = _ScriptedLLM(text="primary answer")
    secondary = _ScriptedLLM(text="secondary answer")

    response = asyncio.run(_chain(primary, secondary).generate(_REQUEST))

    assert response.text == "primary answer"
    assert secondary.calls == 0


def test_failing_primary_falls_over_to_the_secondary() -> None:
    primary = _ScriptedLLM(error="gemini circuit is open")
    secondary = _ScriptedLLM(text="secondary answer")

    response = asyncio.run(_chain(primary, secondary).generate(_REQUEST))

    assert response.text == "secondary answer"
    assert primary.calls == 1
    assert secondary.calls == 1


def test_failover_is_recorded_so_provider_health_stays_visible() -> None:
    # ADR-013's rationale: resilience must not mask an unhealthy provider.
    chain = _chain(_ScriptedLLM(error="down"), _ScriptedLLM(text="ok"))

    asyncio.run(chain.generate(_REQUEST))

    rendered = metrics.render()
    assert (
        'sentinelai_llm_fallbacks_total{primary="gemini",secondary="nvidia"} 1'
        in rendered
    )


def test_both_providers_failing_raises_naming_both() -> None:
    primary = _ScriptedLLM(error="gemini exhausted")
    secondary = _ScriptedLLM(error="nvidia exhausted")

    with pytest.raises(LLMProviderError) as exc_info:
        asyncio.run(_chain(primary, secondary).generate(_REQUEST))

    message = exc_info.value.message
    # One message describing a platform-wide outage, not one provider's blame.
    assert "gemini" in message
    assert "nvidia" in message
    assert "gemini exhausted" in message
    assert "nvidia exhausted" in message


def test_total_outage_still_surfaces_the_port_error_type() -> None:
    # The chain adds an attempt, never a new failure mode: the loop still sees
    # LLMProviderError and degrades to ESCALATED (ADR-013 §3).
    chain = _chain(_ScriptedLLM(error="a"), _ScriptedLLM(error="b"))

    with pytest.raises(LLMProviderError):
        asyncio.run(chain.generate(_REQUEST))
