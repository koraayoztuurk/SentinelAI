"""Graph Analysis Agent contracts (ES-057).

The typed input and product of the ``graph-analysis-agent``
(agent-architecture §6): the agent reasons over an **already-assembled**
snapshot of the investigation's entity neighbourhood and reports notable
graph observations — relationship analysis, attack-path suspicions, lateral
movement, entity correlation. It never traverses the graph itself and never
calls services; assembly is the orchestration layer's responsibility.

These are AI-layer operational structures (not domain objects). ThreatGraph
(ADR-007) remains deferred: this agent consumes the existing Graph Service
surface only — no new traversal semantics are introduced here.
"""

from dataclasses import dataclass
from enum import Enum

from app.ai.errors import GraphAnalysisError
from app.domain.identifiers import EntityId, InvestigationId, RelationshipId
from app.domain.value_objects import Confidence


@dataclass(frozen=True, slots=True)
class EntitySnapshot:
    """The entity facts the Graph Analysis Agent reasons over."""

    id: EntityId
    type: str
    display_name: str
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class RelationshipSnapshot:
    """The relationship facts the Graph Analysis Agent reasons over."""

    id: RelationshipId
    source_entity_id: EntityId
    target_entity_id: EntityId
    type: str
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class GraphContext:
    """An already-assembled snapshot of the investigation's neighbourhood."""

    investigation_id: InvestigationId
    objectives: tuple[str, ...]
    entities: tuple[EntitySnapshot, ...]
    relationships: tuple[RelationshipSnapshot, ...]

    def __post_init__(self) -> None:
        if not self.entities:
            raise GraphAnalysisError(
                "Graph analysis requires at least one entity."
            )


class GraphObservationKind(Enum):
    """The documented graph-analysis vocabulary (agent-architecture §6)."""

    ATTACK_PATH = "attack_path"
    LATERAL_MOVEMENT = "lateral_movement"
    CORRELATION = "correlation"
    ANOMALY = "anomaly"


@dataclass(frozen=True, slots=True)
class GraphObservation:
    """One notable graph observation with its entity provenance."""

    kind: GraphObservationKind
    detail: str
    entities: tuple[EntityId, ...] = ()


@dataclass(frozen=True, slots=True)
class GraphAnalysis:
    """The Graph Analysis Agent's product."""

    investigation_id: InvestigationId
    observations: tuple[GraphObservation, ...]
    summary: str
