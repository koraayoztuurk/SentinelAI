"""Graph Analysis Agent (ES-057).

The concrete ``graph-analysis-agent`` that reasons over an investigation's
assembled entity neighbourhood (agent-architecture §6) and produces one
typed :class:`~app.ai.agents.graph_analysis.analysis.GraphAnalysis` via the
AI Foundation LLM provider: relationship analysis, attack-path suspicions,
lateral-movement detection and entity correlation, reported as observations
with entity provenance. The agent is stateless, never traverses the graph
itself and never calls services.

Reasoning boundary: the agent builds a provider request from the assembled
``GraphContext``, obtains a provider response, and transforms a minimal
structured (JSON) response into the typed analysis. Unknown observation
kinds are ignored; entity references outside the snapshot are discarded
from an observation's provenance (the observation itself is preserved). A
malformed response raises :class:`~app.ai.errors.GraphAnalysisError` — an
empty analysis is not a neutral fallback (it would read as "nothing notable
in the graph").
"""

import json
import logging
from dataclasses import dataclass

from app.ai.agents.base import AgentIdentity
from app.ai.agents.graph_analysis.analysis import (
    GraphAnalysis,
    GraphContext,
    GraphObservation,
    GraphObservationKind,
)
from app.ai.errors import GraphAnalysisError
from app.ai.providers.llm import LLMProvider, LLMRequest

logger = logging.getLogger(__name__)

GRAPH_ANALYSIS_AGENT_IDENTITY = AgentIdentity("graph-analysis-agent")

# Resource bound on reported observations (mirrors the other agents' bounds).
_OBSERVATION_LIMIT = 10


@dataclass(frozen=True, slots=True)
class GraphAnalysisRequest:
    """The typed execution request of the Graph Analysis Agent (ADR-013)."""

    context: GraphContext


class GraphAnalysisAgent:
    """Analyzes the assembled entity neighbourhood (stateless)."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @property
    def identity(self) -> AgentIdentity:
        return GRAPH_ANALYSIS_AGENT_IDENTITY

    async def execute(self, request: GraphAnalysisRequest) -> GraphAnalysis:
        """Run one analysis through the typed agent contract (ADR-013)."""

        return await self.analyze(request.context)

    async def analyze(self, context: GraphContext) -> GraphAnalysis:
        """Reason over the assembled neighbourhood and return one analysis."""

        response = await self._llm.generate(self._build_request(context))
        analysis = self._to_analysis(response.text, context)
        logger.info(
            "graph analysis agent analyzed investigation_id=%s "
            "observations=%s",
            context.investigation_id.value,
            len(analysis.observations),
        )
        return analysis

    @staticmethod
    def _build_request(context: GraphContext) -> LLMRequest:
        # Prompt content is an implementation detail of the documented
        # transformation boundary; it names the exact JSON shape and
        # observation vocabulary `_to_analysis` accepts.
        entity_lines = "\n".join(
            f"- id={entity.id.value} type={entity.type} "
            f"name={entity.display_name} confidence={entity.confidence.value}"
            for entity in context.entities
        )
        relationship_lines = "\n".join(
            f"- {rel.source_entity_id.value} -[{rel.type}]-> "
            f"{rel.target_entity_id.value} confidence={rel.confidence.value}"
            for rel in context.relationships
        )
        prompt = (
            "You are the graph analysis agent of a security investigation "
            "platform. Analyze the entity relationship graph below for "
            "notable structures and respond with ONLY a JSON object (no "
            "prose, no code fences), of exactly this shape:\n"
            '{"summary": "<one-line overall reading of the graph>", '
            '"observations": [{"kind": "<one of: attack_path, '
            'lateral_movement, correlation, anomaly>", '
            '"entities": ["<entity id>"], "detail": "<what the structure '
            'suggests>"}]}\n'
            "Report an empty observations list only when the graph is "
            "genuinely unremarkable; never invent structures.\n"
            "Investigation state:\n"
            f"investigation_id={context.investigation_id.value}\n"
            f"objectives={list(context.objectives)}\n"
            "Entities:\n"
            f"{entity_lines}\n"
            "Relationships:\n"
            f"{relationship_lines if relationship_lines else '- none'}"
        )
        return LLMRequest(prompt=prompt)

    @staticmethod
    def _to_analysis(text: str, context: GraphContext) -> GraphAnalysis:
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise GraphAnalysisError(
                "Graph Analysis Agent received a malformed (non-JSON) "
                "analysis response."
            ) from exc
        if not isinstance(payload, dict):
            raise GraphAnalysisError(
                "Graph Analysis Agent received an unexpected analysis shape."
            )

        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise GraphAnalysisError(
                "Graph Analysis Agent analysis carries no summary."
            )
        raw_observations = payload.get("observations")
        if not isinstance(raw_observations, list):
            raise GraphAnalysisError(
                "Graph Analysis Agent analysis carries no observations list."
            )

        known = {entity.id.value: entity.id for entity in context.entities}
        observations: list[GraphObservation] = []
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
                kind = GraphObservationKind(kind_token)
            except ValueError:
                # Unknown observation kinds are ignored (fixed vocabulary).
                continue
            references = raw.get("entities")
            entities = tuple(
                known[ref]
                for ref in references
                if isinstance(ref, str) and ref in known
            ) if isinstance(references, list) else ()
            observations.append(
                GraphObservation(
                    kind=kind, detail=detail.strip(), entities=entities
                )
            )
            if len(observations) >= _OBSERVATION_LIMIT:
                break

        return GraphAnalysis(
            investigation_id=context.investigation_id,
            observations=tuple(observations),
            summary=summary.strip(),
        )
