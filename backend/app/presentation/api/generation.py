"""Identifier and timestamp generation for the API boundary.

The REST API generates resource identifiers and creation timestamps on the client's
behalf (see api-design and ES-014): this is a presentation/transport concern, so the
"no UUID/clock in domain/services" rule is not violated — the API is a caller that
supplies these values to the backend services.

Generation is expressed through two small, replaceable ports so endpoints stay
deterministic under test: ``IdGenerator`` and ``Clock``. The default
implementations use the standard library; tests override the FastAPI dependencies
with deterministic doubles.
"""

from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4


class IdGenerator(Protocol):
    """Produces opaque, unique resource identifiers."""

    def new_id(self) -> str: ...


class Clock(Protocol):
    """Produces the current time."""

    def now(self) -> datetime: ...


class Uuid4IdGenerator:
    """Default identifier generator backed by ``uuid4``."""

    def new_id(self) -> str:
        return uuid4().hex


class SystemClock:
    """Default clock backed by the system UTC time."""

    def now(self) -> datetime:
        return datetime.now(UTC)


_ID_GENERATOR: IdGenerator = Uuid4IdGenerator()
_CLOCK: Clock = SystemClock()


def get_id_generator() -> IdGenerator:
    """Return the identifier generator (FastAPI dependency)."""

    return _ID_GENERATOR


def get_clock() -> Clock:
    """Return the clock (FastAPI dependency)."""

    return _CLOCK
