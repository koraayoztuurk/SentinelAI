"""Threat Intelligence Agent contracts (ES-059).

The typed input and product of the ``threat-intel-agent`` (agent-architecture
§6): the agent correlates an investigation's facts with **already-retrieved**
external intelligence (MITRE ATT&CK techniques, CVEs — the ES-058 providers)
and reports observations in the documented responsibility vocabulary: IOC
enrichment, CVE correlation, ATT&CK mapping, threat-actor identification. It
never performs lookups itself and never calls services; the Threat Intel Flow
owns retrieval and assembly.

External intelligence stays distinguishable from organizational fact
(rag-architecture §17): every observation carries provenance as the
``source``-relative references of the intelligence items it draws on, bound
to the assembled snapshot — references outside it are discarded.

These are AI-layer operational structures (not domain objects).
"""

from dataclasses import dataclass
from enum import Enum

from app.ai.errors import ThreatIntelAgentError
from app.ai.providers.external import ExternalKnowledgeItem
from app.domain.identifiers import EntityId, InvestigationId


@dataclass(frozen=True, slots=True)
class ThreatIntelEntity:
    """One investigation entity external lookups are focused on."""

    id: EntityId
    type: str
    display_name: str


@dataclass(frozen=True, slots=True)
class ThreatIntelSeed:
    """The investigation-side facts that focus the external lookups."""

    investigation_id: InvestigationId
    objectives: tuple[str, ...]
    entities: tuple[ThreatIntelEntity, ...]


@dataclass(frozen=True, slots=True)
class ThreatIntelContext:
    """An assembled correlation input: investigation facts + intelligence."""

    investigation_id: InvestigationId
    objectives: tuple[str, ...]
    entities: tuple[ThreatIntelEntity, ...]
    intelligence: tuple[ExternalKnowledgeItem, ...]

    def __post_init__(self) -> None:
        if not self.intelligence:
            raise ThreatIntelAgentError(
                "Threat intelligence correlation requires at least one "
                "external intelligence item."
            )


class ThreatIntelObservationKind(Enum):
    """The documented threat-intel vocabulary (agent-architecture §6)."""

    IOC_ENRICHMENT = "ioc_enrichment"
    CVE_CORRELATION = "cve_correlation"
    ATTACK_MAPPING = "attack_mapping"
    THREAT_ACTOR = "threat_actor"


@dataclass(frozen=True, slots=True)
class ThreatIntelObservation:
    """One correlation observation with its intelligence provenance.

    ``references`` are the external item references (``T1021``,
    ``CVE-2021-44228``) from the assembled snapshot the observation draws on.
    """

    kind: ThreatIntelObservationKind
    detail: str
    references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ThreatIntelReport:
    """The Threat Intelligence Agent's product."""

    investigation_id: InvestigationId
    observations: tuple[ThreatIntelObservation, ...]
    summary: str
