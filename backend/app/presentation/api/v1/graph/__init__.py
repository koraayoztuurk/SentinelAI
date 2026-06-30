"""Graph API: the ``/api/v1/graph`` resource family.

Exposes the thin controllers that delegate the entity, relationship and
neighbourhood-traversal operations to the Graph Service.
"""

from app.presentation.api.v1.graph.router import graph_router

__all__ = ["graph_router"]
