"""Correlation context for operational observability.

Carries the per-request correlation identifiers through the current asynchronous
task so that every log record emitted while handling a request can be attributed to
it (end-to-end traceability, audit-and-observability §8). The identifiers are set by
the request-context middleware and read by the logging correlation filter.

This is a cross-cutting, standard-library-only primitive: it is imported by both the
logging configuration and the presentation middleware, so it depends on neither.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Correlation:
    """The correlation identifiers attributed to the current request."""

    request_id: str
    correlation_id: str


_current: ContextVar[Correlation | None] = ContextVar(
    "sentinelai_correlation", default=None
)


def bind(correlation: Correlation) -> Token[Correlation | None]:
    """Bind the correlation for the current context; returns a reset token."""

    return _current.set(correlation)


def reset(token: Token[Correlation | None]) -> None:
    """Restore the correlation to its previous value."""

    _current.reset(token)


def current() -> Correlation | None:
    """Return the correlation bound to the current context, if any."""

    return _current.get()
