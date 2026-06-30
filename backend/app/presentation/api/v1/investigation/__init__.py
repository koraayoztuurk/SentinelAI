"""Investigation API: the ``/api/v1/investigations`` resource family.

Exposes the thin controllers that delegate the investigation, evidence, finding and
report operations to the Investigation Service.
"""

from app.presentation.api.v1.investigation.router import investigation_router

__all__ = ["investigation_router"]
