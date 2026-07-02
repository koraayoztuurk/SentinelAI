"""Platform Observability.

Operational visibility for the backend deployment unit (platform-observability.md),
distinct from the security Audit trail (ES-021). Owns the correlation context that
threads request identifiers through logs (end-to-end traceability) and the in-memory
operational metrics (Platform Health). Cross-cutting and standard-library-only.
"""

from app.observability.correlation import Correlation, bind, current, reset
from app.observability.metrics import PlatformMetrics, metrics

__all__ = [
    "Correlation",
    "bind",
    "current",
    "reset",
    "PlatformMetrics",
    "metrics",
]
