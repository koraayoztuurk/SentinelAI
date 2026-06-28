"""Entity (graph entity).

An Entity is a uniquely identifiable object involved in investigations — a user,
endpoint, IP address, domain, process and so on. Its identity is globally unique
and stable (Domain Rule 3) even though its descriptive attributes may evolve.
Entities are investigation-independent (Domain Rule 8) and therefore carry no
investigation reference.
"""

from dataclasses import dataclass, field

from app.domain.identifiers import EntityId
from app.domain.value_objects import Confidence, EntityType


@dataclass(slots=True)
class Entity:
    """A uniquely identifiable object that may appear across investigations."""

    id: EntityId
    type: EntityType
    display_name: str
    confidence: Confidence
    source: str
    attributes: dict[str, str] = field(default_factory=dict)
    aliases: tuple[str, ...] = ()
