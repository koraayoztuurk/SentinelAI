"""Threat Intelligence Agent (ES-059).

The concrete ``threat-intel-agent`` that correlates an investigation's facts
with already-retrieved external intelligence (agent-architecture §6) and
produces one typed
:class:`~app.ai.agents.threat_intel.report.ThreatIntelReport` via the AI
Foundation LLM provider: IOC enrichment, CVE correlation, MITRE ATT&CK
mapping and threat-actor identification, reported as observations with
intelligence provenance. The agent is stateless, performs no lookups itself
and never calls services.

Reasoning boundary: the agent builds a provider request from the assembled
``ThreatIntelContext``, obtains a provider response, and transforms a minimal
structured (JSON) response into the typed report. Unknown observation kinds
are ignored; references outside the snapshot's intelligence are discarded
from an observation's provenance (the observation itself is preserved) — the
agent must never present external claims the platform did not retrieve. A
malformed response raises :class:`~app.ai.errors.ThreatIntelAgentError` — an
empty report is not a neutral fallback (it would read as "no external
intelligence applies").
"""

import json
import logging
from dataclasses import dataclass

from app.ai.agents.base import AgentIdentity
from app.ai.agents.threat_intel.report import (
    ThreatIntelContext,
    ThreatIntelObservation,
    ThreatIntelObservationKind,
    ThreatIntelReport,
)
from app.ai.errors import ThreatIntelAgentError
from app.ai.providers.llm import LLMProvider, LLMRequest

logger = logging.getLogger(__name__)

THREAT_INTEL_AGENT_IDENTITY = AgentIdentity("threat-intel-agent")

# Resource bounds (mirroring the other agents' bounds): reported observations
# and how much of each intelligence item's content enters the prompt.
_OBSERVATION_LIMIT = 10
_INTEL_CONTENT_LIMIT = 300


@dataclass(frozen=True, slots=True)
class ThreatIntelRequest:
    """The typed execution request of the Threat Intelligence Agent (ADR-013)."""

    context: ThreatIntelContext


class ThreatIntelAgent:
    """Correlates investigation facts with external intelligence (stateless)."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @property
    def identity(self) -> AgentIdentity:
        return THREAT_INTEL_AGENT_IDENTITY

    async def execute(self, request: ThreatIntelRequest) -> ThreatIntelReport:
        """Run one correlation through the typed agent contract (ADR-013)."""

        return await self.correlate(request.context)

    async def correlate(self, context: ThreatIntelContext) -> ThreatIntelReport:
        """Reason over the assembled context and return one report."""

        response = await self._llm.generate(self._build_request(context))
        report = self._to_report(response.text, context)
        logger.info(
            "threat intel agent correlated investigation_id=%s "
            "observations=%s",
            context.investigation_id.value,
            len(report.observations),
        )
        return report

    @staticmethod
    def _build_request(context: ThreatIntelContext) -> LLMRequest:
        # Prompt content is an implementation detail of the documented
        # transformation boundary; it names the exact JSON shape, the
        # observation vocabulary and the reference ids `_to_report` accepts.
        entity_lines = "\n".join(
            f"- id={entity.id.value} type={entity.type} "
            f"name={entity.display_name}"
            for entity in context.entities
        )
        intel_lines = "\n".join(
            f"- ref={item.reference} source={item.source} "
            f"confidence={item.confidence.value:.2f} "
            f"{item.content[:_INTEL_CONTENT_LIMIT]}"
            for item in context.intelligence
        )
        prompt = (
            "You are the threat intelligence agent of a security "
            "investigation platform. Correlate the investigation below with "
            "the retrieved external intelligence and respond with ONLY a "
            "JSON object (no prose, no code fences), of exactly this shape:\n"
            '{"summary": "<one-line overall threat reading>", '
            '"observations": [{"kind": "<one of: ioc_enrichment, '
            'cve_correlation, attack_mapping, threat_actor>", '
            '"references": ["<ref id of a listed intelligence item>"], '
            '"detail": "<what the correlation suggests>"}]}\n'
            "Ground every observation in the listed intelligence items via "
            "their ref ids; never invent intelligence that is not listed. "
            "Report an empty observations list only when nothing listed "
            "genuinely applies.\n"
            "Investigation state:\n"
            f"investigation_id={context.investigation_id.value}\n"
            f"objectives={list(context.objectives)}\n"
            "Entities:\n"
            f"{entity_lines if entity_lines else '- none'}\n"
            "External intelligence:\n"
            f"{intel_lines}"
        )
        return LLMRequest(prompt=prompt)

    @staticmethod
    def _to_report(text: str, context: ThreatIntelContext) -> ThreatIntelReport:
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise ThreatIntelAgentError(
                "Threat Intelligence Agent received a malformed (non-JSON) "
                "report response."
            ) from exc
        if not isinstance(payload, dict):
            raise ThreatIntelAgentError(
                "Threat Intelligence Agent received an unexpected report "
                "shape."
            )

        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ThreatIntelAgentError(
                "Threat Intelligence Agent report carries no summary."
            )
        raw_observations = payload.get("observations")
        if not isinstance(raw_observations, list):
            raise ThreatIntelAgentError(
                "Threat Intelligence Agent report carries no observations "
                "list."
            )

        known = {item.reference for item in context.intelligence}
        observations: list[ThreatIntelObservation] = []
        for raw in raw_observations:
            if not isinstance(raw, dict):
                continue
            kind_token = raw.get("kind")
            detail = raw.get("detail")
            if not isinstance(kind_token, str) or not isinstance(detail, str):
                continue
            if not detail.strip():
                continue
            try:
                kind = ThreatIntelObservationKind(kind_token)
            except ValueError:
                # Unknown observation kinds are ignored (fixed vocabulary).
                continue
            raw_references = raw.get("references")
            references = tuple(
                ref
                for ref in raw_references
                if isinstance(ref, str) and ref in known
            ) if isinstance(raw_references, list) else ()
            observations.append(
                ThreatIntelObservation(
                    kind=kind, detail=detail.strip(), references=references
                )
            )
            if len(observations) >= _OBSERVATION_LIMIT:
                break

        return ThreatIntelReport(
            investigation_id=context.investigation_id,
            observations=tuple(observations),
            summary=summary.strip(),
        )
