"""Operational metrics for platform observability.

A minimal, dependency-free in-memory metrics registry realizing Platform Health
(platform-observability §4): request counts by method and status, aggregate request
duration and process uptime, rendered in the Prometheus text exposition format. It
holds no secrets or request payloads (minimal intrusion / privacy, audit-and-
observability §8).

The registry is a single process-wide instance. Recording takes a short lock;
``render`` copies an immutable snapshot under the lock and then builds the text
outside it, so producing the exposition never blocks request recording.
"""

import threading
from time import monotonic

_METRIC_PREFIX = "sentinelai"


class PlatformMetrics:
    """In-memory operational counters for the backend deployment unit."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, int], int] = {}
        self._duration_ms_sum: float = 0.0
        self._duration_count: int = 0
        self._started_at = monotonic()

    def record_request(self, method: str, status: int, duration_ms: float) -> None:
        """Record a completed request (method, HTTP status and its duration)."""

        key = (method.upper(), status)
        with self._lock:
            self._requests[key] = self._requests.get(key, 0) + 1
            self._duration_ms_sum += duration_ms
            self._duration_count += 1

    def render(self) -> str:
        """Render the current metrics in Prometheus text exposition format."""

        with self._lock:
            requests = dict(self._requests)
            duration_sum = self._duration_ms_sum
            duration_count = self._duration_count
            uptime_seconds = monotonic() - self._started_at

        lines: list[str] = [
            f"# HELP {_METRIC_PREFIX}_requests_total "
            "Total HTTP requests by method and status.",
            f"# TYPE {_METRIC_PREFIX}_requests_total counter",
        ]
        for (method, status), count in sorted(requests.items()):
            lines.append(
                f'{_METRIC_PREFIX}_requests_total'
                f'{{method="{method}",status="{status}"}} {count}'
            )

        lines += [
            f"# HELP {_METRIC_PREFIX}_request_duration_ms_sum "
            "Total request duration in milliseconds.",
            f"# TYPE {_METRIC_PREFIX}_request_duration_ms_sum counter",
            f"{_METRIC_PREFIX}_request_duration_ms_sum {duration_sum:.3f}",
            f"# HELP {_METRIC_PREFIX}_request_duration_ms_count "
            "Number of requests observed.",
            f"# TYPE {_METRIC_PREFIX}_request_duration_ms_count counter",
            f"{_METRIC_PREFIX}_request_duration_ms_count {duration_count}",
            f"# HELP {_METRIC_PREFIX}_uptime_seconds "
            "Seconds since the process started.",
            f"# TYPE {_METRIC_PREFIX}_uptime_seconds gauge",
            f"{_METRIC_PREFIX}_uptime_seconds {uptime_seconds:.3f}",
        ]
        return "\n".join(lines) + "\n"


metrics = PlatformMetrics()
