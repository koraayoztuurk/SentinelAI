"""Memory API: the ``/api/v1/memory`` resource.

Exposes the thin controllers that delegate the Memory Item lifecycle (create, get,
version-supersede update, deprecate, history) to the Memory Service.
"""

from app.presentation.api.v1.memory.router import memory_router

__all__ = ["memory_router"]
