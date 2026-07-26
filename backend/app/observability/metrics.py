"""Operational metrics for platform observability.

A minimal, dependency-free in-memory metrics registry realizing Platform Health
(platform-observability §4): request counts by method and status, aggregate request
duration and process uptime, rendered in the Prometheus text exposition format. It
holds no secrets or request payloads (minimal intrusion / privacy, audit-and-
observability §8).

ES-067 adds the resilience signals, so hardening that works silently is still
observable: provider circuit state, LLM failovers, and the background
projections' dead-letter/deferred counts. ADR-013's rationale requires exactly
this — a breaker that hides provider health would be worse than no breaker.
ES-068 continues it at the request edge: refused requests are counted per
operation, so a limit that is set too tight is visible as a metric rather than
only as a user complaint.

The registry is a single process-wide instance. Recording takes a short lock;
``render`` copies an immutable snapshot under the lock and then builds the text
outside it, so producing the exposition never blocks request recording.
"""

import threading
from dataclasses import dataclass, field
from time import monotonic

_METRIC_PREFIX = "sentinelai"


@dataclass(frozen=True, slots=True)
class MetricsSnapshot:
    """An immutable read of the operational signals at one moment."""

    breaker_states: dict[str, str] = field(default_factory=dict)
    llm_fallbacks: int = 0
    dead_letters: dict[str, int] = field(default_factory=dict)
    deferred_erasures: int = 0
    audit_failures: int = 0
    retention_erased: int = 0
    retention_failed: int = 0

# Circuit state as a gauge value (Prometheus has no string samples).
_BREAKER_STATE_VALUES = {"closed": 0, "half_open": 1, "open": 2}


class PlatformMetrics:
    """In-memory operational counters for the backend deployment unit."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, int], int] = {}
        self._duration_ms_sum: float = 0.0
        self._duration_count: int = 0
        self._started_at = monotonic()
        self._breaker_states: dict[str, str] = {}
        self._llm_fallbacks: dict[tuple[str, str], int] = {}
        self._dead_letters: dict[str, int] = {}
        self._deferred_erasures: int = 0
        self._rate_limited: dict[str, int] = {}
        self._audit_failures: int = 0
        self._retention_erased: int = 0
        self._retention_failed: int = 0

    def record_request(self, method: str, status: int, duration_ms: float) -> None:
        """Record a completed request (method, HTTP status and its duration)."""

        key = (method.upper(), status)
        with self._lock:
            self._requests[key] = self._requests.get(key, 0) + 1
            self._duration_ms_sum += duration_ms
            self._duration_count += 1

    def record_circuit_state(self, provider: str, state: str) -> None:
        """Record a provider circuit-breaker transition (ES-067, ADR-013 §4)."""

        with self._lock:
            self._breaker_states[provider] = state

    def record_llm_fallback(self, primary: str, secondary: str) -> None:
        """Record one failover from ``primary`` to ``secondary`` (ES-067)."""

        with self._lock:
            key = (primary, secondary)
            self._llm_fallbacks[key] = self._llm_fallbacks.get(key, 0) + 1

    def record_dead_letters(self, projection: str, count: int) -> None:
        """Record records retired unprojected by a background projection."""

        if count <= 0:
            return
        with self._lock:
            self._dead_letters[projection] = (
                self._dead_letters.get(projection, 0) + count
            )

    def record_deferred_erasures(self, count: int) -> None:
        """Record payload erasures still owed after a cycle (a gauge, not a sum).

        Erasure never dead-letters (see the erasure projector): a value that
        stays above zero is the signal that erasure is stuck.
        """

        with self._lock:
            self._deferred_erasures = max(0, count)

    def record_rate_limited(self, operation: str) -> None:
        """Record one request refused by the request-edge limiter (ES-068).

        The label is the route template, so its cardinality is bounded by the
        number of API operations rather than by the identities being limited.
        """

        with self._lock:
            self._rate_limited[operation] = (
                self._rate_limited.get(operation, 0) + 1
            )

    def record_audit_failure(self) -> None:
        """Record one audit event the durable sink could not accept (ES-069).

        An unrecorded action is an accountability gap (ADR-018 §8): it must
        never fail the operation, and it must never be quiet.
        """

        with self._lock:
            self._audit_failures += 1

    def record_retention_sweep(self, erased: int, failed: int) -> None:
        """Record one retention sweep cycle (ES-070).

        An automated destructive path has to be visible: ``erased`` is how much
        the platform destroyed on its own, and a ``failed`` count that stays
        above zero means retention is *not* being enforced — a compliance
        condition, not a background nuisance.
        """

        with self._lock:
            self._retention_erased += max(0, erased)
            self._retention_failed += max(0, failed)

    def snapshot(self) -> "MetricsSnapshot":
        """Return an immutable copy of the operational signals (ES-070).

        The Prometheus exposition is for scrapers; this is for the platform's
        own operational surface, which needs the values as data rather than as
        text it would have to parse back.
        """

        with self._lock:
            return MetricsSnapshot(
                breaker_states=dict(self._breaker_states),
                llm_fallbacks=sum(self._llm_fallbacks.values()),
                dead_letters=dict(self._dead_letters),
                deferred_erasures=self._deferred_erasures,
                audit_failures=self._audit_failures,
                retention_erased=self._retention_erased,
                retention_failed=self._retention_failed,
            )

    def render(self) -> str:
        """Render the current metrics in Prometheus text exposition format."""

        with self._lock:
            requests = dict(self._requests)
            duration_sum = self._duration_ms_sum
            duration_count = self._duration_count
            uptime_seconds = monotonic() - self._started_at
            breaker_states = dict(self._breaker_states)
            llm_fallbacks = dict(self._llm_fallbacks)
            dead_letters = dict(self._dead_letters)
            deferred_erasures = self._deferred_erasures
            rate_limited = dict(self._rate_limited)
            audit_failures = self._audit_failures
            retention_erased = self._retention_erased
            retention_failed = self._retention_failed

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

        # --- resilience signals (ES-067) ---
        lines += [
            f"# HELP {_METRIC_PREFIX}_provider_circuit_state "
            "AI provider circuit state (0 closed, 1 half-open, 2 open).",
            f"# TYPE {_METRIC_PREFIX}_provider_circuit_state gauge",
        ]
        for provider, state in sorted(breaker_states.items()):
            value = _BREAKER_STATE_VALUES.get(state, 0)
            lines.append(
                f"{_METRIC_PREFIX}_provider_circuit_state"
                f'{{provider="{provider}"}} {value}'
            )

        lines += [
            f"# HELP {_METRIC_PREFIX}_llm_fallbacks_total "
            "Calls served by the fallback LLM provider.",
            f"# TYPE {_METRIC_PREFIX}_llm_fallbacks_total counter",
        ]
        for (primary, secondary), count in sorted(llm_fallbacks.items()):
            lines.append(
                f"{_METRIC_PREFIX}_llm_fallbacks_total"
                f'{{primary="{primary}",secondary="{secondary}"}} {count}'
            )

        lines += [
            f"# HELP {_METRIC_PREFIX}_projection_dead_letters_total "
            "Outbox records retired without being projected.",
            f"# TYPE {_METRIC_PREFIX}_projection_dead_letters_total counter",
        ]
        for projection, count in sorted(dead_letters.items()):
            lines.append(
                f"{_METRIC_PREFIX}_projection_dead_letters_total"
                f'{{projection="{projection}"}} {count}'
            )

        lines += [
            f"# HELP {_METRIC_PREFIX}_payload_erasures_deferred "
            "Payload erasures still owed after the last cycle.",
            f"# TYPE {_METRIC_PREFIX}_payload_erasures_deferred gauge",
            f"{_METRIC_PREFIX}_payload_erasures_deferred {deferred_erasures}",
        ]

        # --- traffic protection (ES-068) ---
        lines += [
            f"# HELP {_METRIC_PREFIX}_rate_limited_total "
            "Requests refused by the request-edge rate limiter.",
            f"# TYPE {_METRIC_PREFIX}_rate_limited_total counter",
        ]
        for operation, count in sorted(rate_limited.items()):
            lines.append(
                f"{_METRIC_PREFIX}_rate_limited_total"
                f'{{operation="{operation}"}} {count}'
            )

        # --- accountability (ES-069) ---
        lines += [
            f"# HELP {_METRIC_PREFIX}_audit_write_failures_total "
            "Audit events the durable sink could not accept.",
            f"# TYPE {_METRIC_PREFIX}_audit_write_failures_total counter",
            f"{_METRIC_PREFIX}_audit_write_failures_total {audit_failures}",
        ]

        # --- retention enforcement (ES-070) ---
        lines += [
            f"# HELP {_METRIC_PREFIX}_retention_erased_total "
            "Investigations erased by the retention sweep.",
            f"# TYPE {_METRIC_PREFIX}_retention_erased_total counter",
            f"{_METRIC_PREFIX}_retention_erased_total {retention_erased}",
            f"# HELP {_METRIC_PREFIX}_retention_failures_total "
            "Expired investigations the sweep could not erase.",
            f"# TYPE {_METRIC_PREFIX}_retention_failures_total counter",
            f"{_METRIC_PREFIX}_retention_failures_total {retention_failed}",
        ]
        return "\n".join(lines) + "\n"


metrics = PlatformMetrics()
