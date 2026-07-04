"""Graph Service exceptions.

Service-level errors raised by the Graph Service. Each derives from the shared
:class:`~app.shared.exceptions.SentinelAIError` and carries a stable
machine-readable ``code`` so the API layer can translate them into consistent
responses. Only errors tied to an enforced rule are defined here.
"""

from app.shared.exceptions import SentinelAIError


class GraphServiceError(SentinelAIError):
    """Base class for Graph Service errors."""

    code = "graph.error"


class EntityNotFoundError(GraphServiceError):
    """Raised when a referenced entity does not exist.

    Also raised when a relationship references a missing source or target entity.
    """

    code = "graph.entity_not_found"


class RelationshipNotFoundError(GraphServiceError):
    """Raised when a referenced relationship does not exist."""

    code = "graph.relationship_not_found"


class GraphStoreUnavailableError(GraphServiceError):
    """Raised when no graph store is available in the running deployment.

    The first vertical slice binds PostgreSQL only (the Neo4j adapter follows
    a later slice), so graph operations reached at runtime fail with this
    stable, explicit contract. Inside the Planner Service the failure stays
    contained as a failed execution result (planner-service §8) — the
    Investigation Loop observes it and replans or escalates.
    """

    code = "graph.store_unavailable"
