"""Graph Service package.

Exposes the Graph Service and its error types. The repository contract lives in
:mod:`app.application.graph.repositories` and is imported directly by the
infrastructure adapter that implements it.
"""

from app.application.graph.errors import (
    EntityNotFoundError,
    GraphServiceError,
    RelationshipNotFoundError,
)
from app.application.graph.service import GraphService

__all__ = [
    "GraphService",
    "GraphServiceError",
    "EntityNotFoundError",
    "RelationshipNotFoundError",
]
