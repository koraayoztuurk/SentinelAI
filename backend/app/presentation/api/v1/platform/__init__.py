"""Platform status API (ES-070).

The operational surface of the production-hardening milestone: one read of the
platform's own posture — readiness, resilience, data lifecycle, audit — for the
people responsible for operating it.
"""

from app.presentation.api.v1.platform.router import platform_router

__all__ = ["platform_router"]
