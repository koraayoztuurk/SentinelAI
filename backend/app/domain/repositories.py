"""Repository port.

Defines the persistence seam owned by the domain layer. Its single purpose is to
establish the architectural dependency direction: infrastructure repository
implementations depend inward on this domain-defined abstraction, rather than the
domain depending on infrastructure.

This port is intentionally a pure marker. It declares no persistence operations.
Concrete repository contracts — their methods, granularity and store-specific
behaviour — are owned by the backend services that own the corresponding data
(per ADR-003 and ADR-004) and are introduced by their specifications.
"""

from typing import Protocol


class Repository(Protocol):
    """Marker port for persistence repositories.

    Establishes the domain-defined boundary that infrastructure repository
    implementations depend on. It deliberately declares no methods or attributes;
    operation contracts belong to the owning services.
    """
